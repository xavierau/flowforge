"""Authentication API endpoints for user registration, login, and token management."""

from datetime import datetime
from typing import Optional
import re
import secrets

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from jose import JWTError

from app.database import get_db
from app.dependencies.rate_limit import limiter
from app.models import User, Tenant, Role
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    LogoutRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
    AcceptInvitationRequest,
    AuthResponse,
    TokenResponse,
    MessageResponse,
    UserProfileResponse,
    UserInfo,
    TenantInfo,
)
from app.services.auth_service import auth_service
from app.services.permission_service import PermissionService
from app.services.platform_settings_service import PlatformSettingsService
from app.services.credit_service import CreditService
from app.dependencies.auth import get_current_active_user
from app.config import settings
from app.tasks.email_tasks import (
    send_password_reset_email_task,
    send_verification_email_task,
    send_welcome_email_task,
)

router = APIRouter()


def _generate_slug(name: str) -> str:
    """
    Generate a URL-safe slug from a name.

    Args:
        name: The name to convert to a slug

    Returns:
        A URL-safe slug (lowercase, alphanumeric with hyphens)
    """
    # Convert to lowercase
    slug = name.lower()
    # Replace spaces and special chars with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    # Collapse multiple hyphens
    slug = re.sub(r'-+', '-', slug)
    return slug


def _make_slug_unique(db: Session, base_slug: str) -> str:
    """
    Ensure slug is unique by appending a number if necessary.

    Args:
        db: Database session
        base_slug: The base slug to make unique

    Returns:
        A unique slug
    """
    slug = base_slug
    counter = 1

    while db.query(Tenant).filter(Tenant.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


@router.post(
    "/auth/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account and optionally create a new tenant organization"
)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
) -> AuthResponse:
    """
    Register a new user account.

    Workflow:
    1. Check if email already exists (409 Conflict)
    2. Create tenant if tenant_name provided, otherwise use default tenant
    3. Get default "member" role
    4. Hash password
    5. Create user with is_verified=False
    6. Generate email verification token (TODO: send email)
    7. Generate access + refresh tokens
    8. Return user, tenant, and tokens

    Args:
        request: Registration request with email, password, optional tenant_name
        db: Database session

    Returns:
        AuthResponse with user, tenant, and tokens

    Raises:
        HTTPException 409: Email already exists
        HTTPException 400: Invalid role configuration
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Get trial credits amount from platform settings
    settings_service = PlatformSettingsService(db)
    trial_credits_amount = settings_service.get_trial_credits_amount()

    # Create or get tenant
    tenant: Optional[Tenant] = None
    is_new_tenant = False

    if request.tenant_name:
        # Create new tenant
        base_slug = _generate_slug(request.tenant_name)
        unique_slug = _make_slug_unique(db, base_slug)

        tenant = Tenant(
            name=request.tenant_name,
            slug=unique_slug,
            status="active",
            subscription_plan="free",
            cached_balance=0,  # Will be set via credit transaction
            tenant_metadata={}
        )
        db.add(tenant)
        db.flush()  # Get tenant.id without committing
        is_new_tenant = True
    else:
        # Use default tenant (for invitation flow or single-tenant mode)
        # For now, create a default tenant if none exists
        tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
        if not tenant:
            tenant = Tenant(
                name="Default Organization",
                slug="default",
                status="active",
                subscription_plan="free",
                cached_balance=0,  # Will be set via credit transaction
                tenant_metadata={}
            )
            db.add(tenant)
            db.flush()
            is_new_tenant = True

    # Get default "member" role
    member_role = db.query(Role).filter(Role.name == "member").first()
    if not member_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Default role 'member' not found. Database may need seeding."
        )

    # Hash password
    hashed_password = auth_service.hash_password(request.password)

    # Generate email verification token
    verification_token = auth_service.generate_verification_token()

    # Create user
    user = User(
        email=request.email,
        hashed_password=hashed_password,
        full_name=request.full_name,
        tenant_id=tenant.id,
        role_id=member_role.id,
        is_active=True,
        is_verified=False,  # Require email verification
        email_verification_token=verification_token,
        locale="en"
    )

    db.add(user)

    # FIXED: Add trial credits BEFORE commit to make registration atomic
    # If credit addition fails, entire registration rolls back
    if is_new_tenant and trial_credits_amount > 0:
        credit_service = CreditService(db)
        try:
            credit_service.add_credits(
                tenant_id=tenant.id,
                amount=trial_credits_amount,
                transaction_type="trial_signup",
                reference_type="tenant_registration",
                reference_id=str(tenant.id),
                description=f"Trial credits for new tenant signup: {tenant.name}"
            )
        except Exception as e:
            # If credit addition fails, rollback entire registration
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Registration failed: Unable to allocate trial credits. Please try again."
            )

    # Commit user, tenant, and credits together as one atomic transaction
    try:
        db.commit()
        db.refresh(user)
        db.refresh(tenant)
    except IntegrityError as e:
        db.rollback()
        # Handle race condition where email was registered between check and insert
        if "email" in str(e.orig).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

    # Send verification email asynchronously via Celery task
    verification_url = f"{settings.frontend_url}/verify-email?token={verification_token}"
    send_verification_email_task.delay(
        to_email=user.email,
        verification_url=verification_url,
        user_name=user.full_name,
        expires_in_hours=48,
    )

    # Get user's role for JWT token
    user_role = db.query(Role).filter(Role.id == user.role_id).first()
    role_name = user_role.name if user_role else None

    # Generate tokens with role information
    access_token = auth_service.create_access_token(
        user_id=str(user.id),
        tenant_id=str(tenant.id),
        additional_claims={"role_name": role_name} if role_name else None
    )
    refresh_token = auth_service.create_refresh_token(user_id=str(user.id))

    # Store refresh token
    user.refresh_token = refresh_token
    db.commit()

    return AuthResponse(
        user=UserInfo.model_validate(user),
        tenant=TenantInfo.model_validate(tenant),
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post(
    "/auth/login",
    response_model=AuthResponse,
    summary="Login with email and password",
    description="Authenticate user and return access/refresh tokens"
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    login_request: LoginRequest,
    db: Session = Depends(get_db)
) -> AuthResponse:
    """
    Authenticate user with email and password.

    Workflow:
    1. Find user by email
    2. Verify password
    3. Check if user is active
    4. Update last_login timestamp
    5. Generate new access + refresh tokens
    6. Store refresh token
    7. Return user, tenant, and tokens

    Args:
        request: Login request with email and password
        db: Database session

    Returns:
        AuthResponse with user, tenant, and tokens

    Raises:
        HTTPException 401: Invalid credentials or inactive user
    """
    # Find user
    user = db.query(User).filter(User.email == login_request.email).first()

    if not user:
        # Generic error message to prevent email enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Verify password
    if not auth_service.verify_password(login_request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive. Please contact support."
        )

    # Update last_login
    user.last_login = datetime.utcnow()

    # Get tenant
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User tenant not found"
        )

    # Get user's role for JWT token
    role = db.query(Role).filter(Role.id == user.role_id).first()
    role_name = role.name if role else None

    # Generate tokens with role information
    access_token = auth_service.create_access_token(
        user_id=str(user.id),
        tenant_id=str(tenant.id),
        additional_claims={"role_name": role_name} if role_name else None
    )
    refresh_token = auth_service.create_refresh_token(user_id=str(user.id))

    # Store refresh token
    user.refresh_token = refresh_token
    db.commit()

    return AuthResponse(
        user=UserInfo.model_validate(user),
        tenant=TenantInfo.model_validate(tenant),
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post(
    "/auth/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Generate new access and refresh tokens using a valid refresh token"
)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Refresh access token using a valid refresh token.

    Workflow:
    1. Verify refresh token signature and expiration
    2. Extract user_id from token
    3. Verify token matches user's stored refresh_token
    4. Generate new access + refresh tokens
    5. Update stored refresh_token
    6. Return new tokens

    Args:
        request: Refresh token request
        db: Database session

    Returns:
        TokenResponse with new access and refresh tokens

    Raises:
        HTTPException 401: Invalid or expired token
        HTTPException 404: User not found
    """
    try:
        # Verify refresh token
        payload = auth_service.verify_token(
            request.refresh_token,
            token_type="refresh"
        )
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

    except ValueError as e:
        # Token type mismatch
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except JWTError as e:
        # Invalid signature, expired, or malformed
        error_msg = str(e).lower()
        if "expired" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired. Please login again."
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify stored refresh token matches
    if user.refresh_token != request.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked or is invalid"
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive"
        )

    # Get user's role for JWT token
    role = db.query(Role).filter(Role.id == user.role_id).first()
    role_name = role.name if role else None

    # Generate new tokens with role information
    access_token = auth_service.create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        additional_claims={"role_name": role_name} if role_name else None
    )
    new_refresh_token = auth_service.create_refresh_token(user_id=str(user.id))

    # Update stored refresh token
    user.refresh_token = new_refresh_token
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )


@router.post(
    "/auth/logout",
    response_model=MessageResponse,
    summary="Logout user",
    description="Invalidate refresh token and logout user"
)
async def logout(
    request: LogoutRequest = LogoutRequest(),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Logout user by invalidating refresh token.

    Workflow:
    1. Extract current user from Bearer token
    2. Clear stored refresh_token (set to NULL)
    3. Return success message

    Args:
        request: Optional logout request (may contain refresh_token)
        current_user: Current authenticated user
        db: Database session

    Returns:
        MessageResponse confirming logout
    """
    # Invalidate refresh token
    current_user.refresh_token = None
    db.commit()

    return MessageResponse(message="Logged out successfully")


@router.post(
    "/auth/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset",
    description="Generate password reset token and send email (placeholder)"
)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    forgot_request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Initiate password reset process.

    Workflow:
    1. Find user by email
    2. Generate reset token
    3. Set token expiry (6 hours)
    4. Store token in user record
    5. TODO: Send reset email
    6. Return generic success message (security: don't reveal if email exists)

    Args:
        request: Forgot password request with email
        db: Database session

    Returns:
        MessageResponse (always success to prevent email enumeration)
    """
    # Find user (but don't reveal if email doesn't exist)
    user = db.query(User).filter(User.email == forgot_request.email).first()

    if user:
        # Generate reset token
        reset_token = auth_service.generate_reset_token()
        reset_expires = auth_service.get_password_reset_expires()

        # Store token and expiry
        user.password_reset_token = reset_token
        user.password_reset_expires = reset_expires
        db.commit()

        # Send password reset email asynchronously via Celery task
        reset_url = f"{settings.frontend_url}/reset-password?token={reset_token}"
        send_password_reset_email_task.delay(
            to_email=user.email,
            reset_url=reset_url,
            user_name=user.full_name,
            expires_in_hours=6,  # Match the token expiry
        )

    # Always return success to prevent email enumeration
    return MessageResponse(
        message="If the email exists, a password reset link has been sent"
    )


@router.post(
    "/auth/reset-password",
    response_model=MessageResponse,
    summary="Reset password with token",
    description="Complete password reset using token from email"
)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    reset_request: ResetPasswordRequest,
    db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Complete password reset using token.

    Workflow:
    1. Find user by reset token
    2. Verify token hasn't expired
    3. Hash new password
    4. Update password
    5. Clear reset token and expiry
    6. Invalidate all refresh tokens (force re-login)
    7. Return success message

    Args:
        request: Reset password request with token and new password
        db: Database session

    Returns:
        MessageResponse confirming password reset

    Raises:
        HTTPException 400: Invalid or expired token
    """
    # Find user by reset token
    user = db.query(User).filter(
        User.password_reset_token == reset_request.token
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Check token expiry
    if not user.password_reset_expires or user.password_reset_expires < datetime.utcnow():
        # Clear expired token
        user.password_reset_token = None
        user.password_reset_expires = None
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Please request a new one."
        )

    # Hash new password
    user.hashed_password = auth_service.hash_password(reset_request.new_password)

    # Clear reset token
    user.password_reset_token = None
    user.password_reset_expires = None

    # Invalidate all refresh tokens (force re-login everywhere)
    user.refresh_token = None

    db.commit()

    return MessageResponse(message="Password reset successfully")


@router.post(
    "/auth/verify-email",
    response_model=MessageResponse,
    summary="Verify email address",
    description="Complete email verification using token from email"
)
async def verify_email(
    request: VerifyEmailRequest,
    db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Verify user's email address.

    Workflow:
    1. Find user by verification token
    2. Set is_verified=True
    3. Clear verification token
    4. Return success message

    Args:
        request: Email verification request with token
        db: Database session

    Returns:
        MessageResponse confirming email verification

    Raises:
        HTTPException 400: Invalid token or already verified
    """
    # Find user by verification token
    user = db.query(User).filter(
        User.email_verification_token == request.token
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )

    # Check if already verified
    if user.is_verified:
        return MessageResponse(message="Email already verified")

    # Mark as verified
    user.is_verified = True
    user.email_verification_token = None
    db.commit()

    return MessageResponse(message="Email verified successfully")


@router.post(
    "/auth/accept-invitation",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Accept invitation and set up account",
    description="Complete invitation acceptance by setting password and activating account"
)
@limiter.limit("5/minute")
async def accept_invitation(
    request: Request,
    invitation_request: AcceptInvitationRequest,
    db: Session = Depends(get_db)
) -> AuthResponse:
    """
    Accept an invitation and complete account setup.

    Workflow:
    1. Find user by invitation token (email_verification_token)
    2. Validate user exists and is in pending state
    3. Hash password
    4. Update user: set password, activate, verify, clear token
    5. Generate access + refresh tokens
    6. Return user, tenant, and tokens (same as login)

    Args:
        request: Accept invitation request with token, password, optional full_name
        db: Database session

    Returns:
        AuthResponse with user, tenant, and tokens

    Raises:
        HTTPException 400: Invalid invitation token
        HTTPException 400: Invitation already accepted
    """
    # Find user by invitation token with eager loading of tenant and role
    # This uses a single query with JOINs instead of 3 separate queries
    user = db.query(User).options(
        joinedload(User.tenant),
        joinedload(User.role)
    ).filter(
        User.email_verification_token == invitation_request.token
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invitation token"
        )

    # Check if invitation has expired
    if user.invitation_expires and user.invitation_expires < datetime.utcnow():
        # Clear expired token
        user.email_verification_token = None
        user.invitation_expires = None
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired. Please request a new invitation."
        )

    # Check if invitation already accepted (user is already active)
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation already accepted"
        )

    # Hash password
    hashed_password = auth_service.hash_password(invitation_request.password)

    # Update user record
    user.hashed_password = hashed_password
    user.is_verified = True
    user.is_active = True
    user.email_verification_token = None  # Clear token (single use)
    user.invitation_expires = None  # Clear expiration after acceptance
    user.last_login = datetime.utcnow()

    # Set full_name if provided and user doesn't already have one
    if invitation_request.full_name and not user.full_name:
        user.full_name = invitation_request.full_name

    # Access tenant and role from eagerly loaded relationships
    tenant = user.tenant
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User tenant not found"
        )

    # Get role name from eagerly loaded relationship
    role_name = user.role.name if user.role else None

    # Generate tokens with role information
    access_token = auth_service.create_access_token(
        user_id=str(user.id),
        tenant_id=str(tenant.id),
        additional_claims={"role_name": role_name} if role_name else None
    )
    refresh_token = auth_service.create_refresh_token(user_id=str(user.id))

    # Store refresh token
    user.refresh_token = refresh_token
    db.commit()
    db.refresh(user)
    db.refresh(tenant)

    # Send welcome email asynchronously via Celery task
    login_url = f"{settings.frontend_url}/login"
    send_welcome_email_task.delay(
        to_email=user.email,
        login_url=login_url,
        user_name=user.full_name,
        tenant_name=tenant.name,
    )

    return AuthResponse(
        user=UserInfo.model_validate(user),
        tenant=TenantInfo.model_validate(tenant),
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.get(
    "/auth/me",
    response_model=UserProfileResponse,
    summary="Get current user profile",
    description="Get authenticated user's profile, tenant, and permissions"
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> UserProfileResponse:
    """
    Get current user's profile information.

    Workflow:
    1. Extract current user from Bearer token (via dependency)
    2. Load tenant information
    3. Get user permissions via PermissionService
    4. Return user, tenant, and permissions

    Args:
        current_user: Current authenticated user (from dependency)
        db: Database session

    Returns:
        UserProfileResponse with user, tenant, and permissions

    Raises:
        HTTPException 404: Tenant not found
    """
    # Get tenant
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    # Get user permissions
    permission_service = PermissionService(db)
    permissions = permission_service.get_user_permissions(current_user)

    return UserProfileResponse(
        user=UserInfo.model_validate(current_user),
        tenant=TenantInfo.model_validate(tenant),
        permissions=permissions
    )
