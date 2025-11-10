/**
 * Navbar Component
 *
 * Top navigation bar for authenticated layout.
 * Displays app branding, user menu, and mobile sidebar toggle.
 *
 * Design Principles:
 * - Single Responsibility: Handles only top navigation concerns
 * - Composability: Uses shadcn/ui DropdownMenu and Avatar components
 * - No side effects: All interactions handled through callbacks
 */

import { Menu, LogOut, User as UserIcon } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { clearTokens } from '@/services/auth.service';
import type { User } from '@/types/user';

interface NavbarProps {
  user: User;
  onMobileMenuToggle: () => void;
}

/**
 * Get user initials for avatar fallback
 * Extracts first letter of first and last name
 */
function getUserInitials(name: string): string {
  const parts = name.split(' ');
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }
  return name.substring(0, 2).toUpperCase();
}

export function Navbar({ user, onMobileMenuToggle }: NavbarProps) {
  const navigate = useNavigate();

  const handleLogout = () => {
    clearTokens();
    navigate('/login');
  };

  const handleProfile = () => {
    // TODO: Navigate to profile page when implemented
    console.log('Navigate to profile');
  };

  return (
    <nav className="border-b bg-white">
      <div className="flex h-16 items-center px-4 gap-4">
        {/* Mobile Menu Toggle */}
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={onMobileMenuToggle}
          aria-label="Toggle sidebar"
        >
          <Menu className="h-5 w-5" />
        </Button>

        {/* App Logo/Name */}
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-bold text-gray-900">
            AI Document Processor
          </h1>
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* User Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className="relative h-10 w-10 rounded-full"
              aria-label="User menu"
            >
              <Avatar className="h-10 w-10">
                <AvatarFallback className="bg-primary text-primary-foreground">
                  {getUserInitials(user.name)}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56" align="end" forceMount>
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col gap-1">
                <p className="text-sm font-medium leading-none">{user.name}</p>
                <p className="text-xs leading-none text-muted-foreground">
                  {user.email}
                </p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleProfile}>
              <UserIcon className="mr-2 h-4 w-4" />
              <span>Profile</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout}>
              <LogOut className="mr-2 h-4 w-4" />
              <span>Log out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </nav>
  );
}
