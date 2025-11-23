"""
Credit system health checks and monitoring.

Provides endpoints and background tasks to monitor credit system integrity
and detect billing violations.
"""

from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy import text, func
from sqlalchemy.orm import Session

from app.models import ExtractionJob, Tenant, CreditTransaction
from app.models.enums import CreditTransactionType, ReferenceType


class CreditHealthMonitor:
    """
    Monitor credit system health and detect violations.

    Checks for:
    - Completed jobs without credit deductions
    - Negative tenant balances
    - Duplicate credit transactions
    - Balance mismatches (cached vs calculated)
    """

    def __init__(self, db: Session):
        self.db = db

    def check_all_violations(self) -> List[Dict[str, Any]]:
        """
        Run all credit health checks.

        Returns:
            List of violation dictionaries with severity, type, and details
        """
        violations = []

        # Check 1: Completed jobs without credit deductions
        jobs_violation = self._check_completed_jobs_without_credits()
        if jobs_violation:
            violations.append(jobs_violation)

        # Check 2: Negative balances
        negative_balance_violation = self._check_negative_balances()
        if negative_balance_violation:
            violations.append(negative_balance_violation)

        # Check 3: Duplicate transactions
        duplicate_violation = self._check_duplicate_transactions()
        if duplicate_violation:
            violations.append(duplicate_violation)

        # Check 4: Balance mismatches
        mismatch_violation = self._check_balance_mismatches()
        if mismatch_violation:
            violations.append(mismatch_violation)

        return violations

    def _check_completed_jobs_without_credits(self) -> Dict[str, Any] | None:
        """Check for completed jobs that haven't deducted credits."""
        query = text("""
            SELECT COUNT(*) as count
            FROM extraction_jobs
            WHERE status = 'completed'
              AND (
                  credits_deducted = FALSE
                  OR credits_deducted IS NULL
                  OR credit_transaction_id IS NULL
              )
        """)

        result = self.db.execute(query).scalar()

        if result and result > 0:
            # Get sample jobs for investigation
            sample_query = text("""
                SELECT id, document_id, completed_at
                FROM extraction_jobs
                WHERE status = 'completed'
                  AND (
                      credits_deducted = FALSE
                      OR credits_deducted IS NULL
                      OR credit_transaction_id IS NULL
                  )
                LIMIT 5
            """)
            samples = self.db.execute(sample_query).fetchall()

            return {
                "severity": "CRITICAL",
                "type": "completed_jobs_without_credits",
                "message": f"{result} completed jobs without credit deductions",
                "count": result,
                "sample_job_ids": [str(s.id) for s in samples],
                "timestamp": datetime.utcnow().isoformat()
            }

        return None

    def _check_negative_balances(self) -> Dict[str, Any] | None:
        """Check for tenants with negative credit balances."""
        query = text("""
            SELECT
                COUNT(*) as count,
                MIN(cached_balance) as min_balance,
                ARRAY_AGG(id) FILTER (WHERE cached_balance < 0) as tenant_ids
            FROM tenants
            WHERE cached_balance < 0
        """)

        result = self.db.execute(query).first()

        if result and result.count > 0:
            return {
                "severity": "CRITICAL",
                "type": "negative_balances",
                "message": f"{result.count} tenants with negative balance (lowest: {result.min_balance})",
                "count": result.count,
                "min_balance": float(result.min_balance),
                "tenant_ids": [str(tid) for tid in (result.tenant_ids or [])[:5]],  # First 5
                "timestamp": datetime.utcnow().isoformat()
            }

        return None

    def _check_duplicate_transactions(self) -> Dict[str, Any] | None:
        """Check for jobs with multiple credit transactions."""
        query = text("""
            SELECT
                reference_id as job_id,
                COUNT(*) as transaction_count
            FROM credit_transactions
            WHERE reference_type = :reference_type
            GROUP BY reference_id
            HAVING COUNT(*) > 1
            LIMIT 10
        """)

        duplicates = self.db.execute(
            query,
            {"reference_type": ReferenceType.EXTRACTION_JOB.value}
        ).fetchall()

        if duplicates:
            return {
                "severity": "HIGH",
                "type": "duplicate_transactions",
                "message": f"{len(duplicates)} jobs have duplicate credit transactions",
                "count": len(duplicates),
                "sample_jobs": [
                    {
                        "job_id": str(d.job_id),
                        "transaction_count": d.transaction_count
                    }
                    for d in duplicates[:5]
                ],
                "timestamp": datetime.utcnow().isoformat()
            }

        return None

    def _check_balance_mismatches(self) -> Dict[str, Any] | None:
        """Check for mismatches between cached and calculated balances."""
        query = text("""
            WITH calculated_balances AS (
                SELECT
                    tenant_id,
                    COALESCE(SUM(amount), 0) as calculated_balance
                FROM credit_transactions
                GROUP BY tenant_id
            )
            SELECT
                t.id as tenant_id,
                t.cached_balance,
                cb.calculated_balance,
                ABS(t.cached_balance - cb.calculated_balance) as diff
            FROM tenants t
            JOIN calculated_balances cb ON cb.tenant_id = t.id
            WHERE ABS(t.cached_balance - cb.calculated_balance) > 0.01
            LIMIT 10
        """)

        mismatches = self.db.execute(query).fetchall()

        if mismatches:
            total_discrepancy = sum(m.diff for m in mismatches)

            return {
                "severity": "HIGH",
                "type": "balance_mismatches",
                "message": f"{len(mismatches)} tenants have balance mismatches (total discrepancy: {total_discrepancy:.2f} credits)",
                "count": len(mismatches),
                "total_discrepancy": float(total_discrepancy),
                "sample_tenants": [
                    {
                        "tenant_id": str(m.tenant_id),
                        "cached": float(m.cached_balance),
                        "calculated": float(m.calculated_balance),
                        "diff": float(m.diff)
                    }
                    for m in mismatches[:5]
                ],
                "timestamp": datetime.utcnow().isoformat()
            }

        return None

    def get_health_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive health summary.

        Returns:
            Dictionary with overall status and violation details
        """
        violations = self.check_all_violations()

        if not violations:
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "violations": []
            }

        # Determine overall status based on severity
        has_critical = any(v["severity"] == "CRITICAL" for v in violations)

        return {
            "status": "unhealthy" if has_critical else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "violations": violations,
            "critical_count": sum(1 for v in violations if v["severity"] == "CRITICAL"),
            "high_count": sum(1 for v in violations if v["severity"] == "HIGH"),
        }
