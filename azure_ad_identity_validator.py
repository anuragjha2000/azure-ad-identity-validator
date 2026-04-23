#!/usr/bin/env python3
"""
Azure AD User Provisioning & Identity Validation Project
=========================================================
Project: User Identity Lifecycle Management in Hybrid Azure AD Environment
Author: Anurag Kumar Jha
Date: 2026-04-24
Purpose: Automate user provisioning validation, access package verification, 
         and identity compliance checks in hybrid Azure AD environments.

This project demonstrates:
- Azure SDK integration for identity management
- User account provisioning workflows
- Group membership validation
- Access package verification
- Automated compliance reporting
- Audit trail logging
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import requests
from dataclasses import dataclass, asdict

# Configure logging for audit trail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('identity_audit_log.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class UserAccount:
    """Represents an Azure AD user account with validation metadata."""
    user_id: str
    display_name: str
    user_principal_name: str
    mail: str
    account_enabled: bool
    invitation_state: str  # PendingAcceptance, Accepted, Failed
    created_timestamp: str
    last_sign_in: Optional[str] = None
    
    
@dataclass
class GroupMembership:
    """Represents user's group and access package assignments."""
    group_id: str
    group_name: str
    group_type: str  # Common, AccessPackage, City
    assigned_timestamp: str
    is_dynamic: bool = False


@dataclass
class AccessPackage:
    """Represents Azure AD access package assignment."""
    access_package_id: str
    access_package_name: str
    catalog_id: str
    assignment_status: str  # Delivered, Partial, Expired
    access_review_date: str


class AzureADIdentityValidator:
    """
    Validates Azure AD user identities, group memberships, and access packages
    in a hybrid cloud environment.
    
    This class mimics real Azure AD validation workflows for demonstration.
    In production, would use Azure SDK (azure-identity, azure-graphrbac).
    """
    
    def __init__(self, tenant_id: str, mock_mode: bool = True):
        """
        Initialize the validator.
        Args:
            tenant_id: Azure AD tenant ID
            mock_mode: If True, uses sample data for demonstration
        """
        self.tenant_id = tenant_id
        self.mock_mode = mock_mode
        self.users_database = []
        self.validation_results = []
        
        logger.info(f"Initialised AzureADIdentityValidator for tenant: {tenant_id}")
    
    def create_user_account(self, user_data: Dict) -> UserAccount:
        """
        Simulate user account creation in Azure AD.
        In production: uses Graph API /users endpoint
        """
        user = UserAccount(
            user_id=user_data.get('user_id'),
            display_name=user_data.get('display_name'),
            user_principal_name=user_data.get('upn'),
            mail=user_data.get('mail'),
            account_enabled=user_data.get('enabled', True),
            invitation_state=user_data.get('invitation_state', 'Accepted'),
            created_timestamp=datetime.now().isoformat()
        )
        
        self.users_database.append(user)
        logger.info(f"User created: {user.display_name} ({user.user_principal_name})")
        return user
    
    def validate_user_existence(self, upn: str) -> Dict:
        """
        Validates if user account exists in Azure AD.
        Checks: UPN presence, account state, invitation status
        """
        validation = {
            'validation_name': 'User Existence',
            'upn': upn,
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }
        
        # Simulate finding user
        user = next((u for u in self.users_database if u.user_principal_name == upn), None)
        
        if user:
            validation['checks']['user_exists_in_aad'] = True
            validation['checks']['user_id'] = user.user_id
            validation['checks']['account_enabled'] = user.account_enabled
            validation['checks']['invitation_state'] = user.invitation_state
            validation['checks']['created_date'] = user.created_timestamp
            validation['status'] = 'PASS'
            logger.info(f"✓ User validation PASSED for {upn}")
        else:
            validation['checks']['user_exists_in_aad'] = False
            validation['status'] = 'FAIL'
            logger.warning(f"✗ User validation FAILED for {upn} - user not found")
        
        return validation
    
    def validate_name_matching(self, upn: str, expected_display_name: str) -> Dict:
        """
        Validates that AAD display name matches SuccessFactors record.
        Critical for identity governance.
        """
        validation = {
            'validation_name': 'Name Matching (AAD ↔ SuccessFactors)',
            'upn': upn,
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }
        
        user = next((u for u in self.users_database if u.user_principal_name == upn), None)
        
        if user:
            name_matches = user.display_name.lower() == expected_display_name.lower()
            validation['checks']['aad_display_name'] = user.display_name
            validation['checks']['expected_name'] = expected_display_name
            validation['checks']['names_match'] = name_matches
            validation['status'] = 'PASS' if name_matches else 'FAIL'
            
            if name_matches:
                logger.info(f"✓ Name match validated: {user.display_name}")
            else:
                logger.warning(f"✗ Name mismatch: AAD='{user.display_name}' vs SF='{expected_display_name}'")
        else:
            validation['status'] = 'SKIP'
            logger.info(f"⊘ Name validation skipped - user not found")
        
        return validation
    
    def validate_group_membership(self, upn: str, expected_groups: List[str]) -> Dict:
        """
        Validates user is member of correct Azure AD groups.
        Prevents duplicate memberships and orphaned users.
        """
        validation = {
            'validation_name': 'Group Membership',
            'upn': upn,
            'timestamp': datetime.now().isoformat(),
            'checks': {
                'expected_groups': expected_groups,
                'actual_groups': [],
                'groups_match': False,
                'duplicate_memberships': False,
                'orphaned_user': False
            }
        }
        
        # Simulate group membership lookup
        actual_groups = self._get_user_groups(upn)
        validation['checks']['actual_groups'] = actual_groups
        
        # Check for exact match
        groups_match = set(actual_groups) == set(expected_groups)
        validation['checks']['groups_match'] = groups_match
        
        # Check for duplicates
        has_duplicates = len(actual_groups) != len(set(actual_groups))
        validation['checks']['duplicate_memberships'] = has_duplicates
        
        # Check if orphaned (no groups)
        is_orphaned = len(actual_groups) == 0
        validation['checks']['orphaned_user'] = is_orphaned
        
        # Determine overall status
        if groups_match and not has_duplicates and not is_orphaned:
            validation['status'] = 'PASS'
            logger.info(f"✓ Group membership validated for {upn}")
        else:
            validation['status'] = 'FAIL'
            if has_duplicates:
                logger.warning(f"✗ Duplicate group memberships detected for {upn}")
            if is_orphaned:
                logger.warning(f"✗ User {upn} has no group assignments (orphaned)")
            if not groups_match:
                logger.warning(f"✗ Group mismatch for {upn}")
        
        return validation
    
    def validate_access_package(self, upn: str, expected_access_package: str) -> Dict:
        """
        Validates user has correct access package assignment.
        Access packages control entitlements in identity governance.
        """
        validation = {
            'validation_name': 'Access Package Assignment',
            'upn': upn,
            'timestamp': datetime.now().isoformat(),
            'checks': {
                'expected_package': expected_access_package,
                'package_assigned': False,
                'assignment_status': None,
                'delivery_date': None
            }
        }
        
        # Simulate access package lookup
        assigned_package = self._get_user_access_package(upn, expected_access_package)
        
        if assigned_package:
            validation['checks']['package_assigned'] = True
            validation['checks']['assignment_status'] = assigned_package.get('status')
            validation['checks']['delivery_date'] = assigned_package.get('delivery_date')
            validation['status'] = 'PASS' if assigned_package.get('status') == 'Delivered' else 'PARTIAL'
            logger.info(f"✓ Access package '{expected_access_package}' assigned to {upn}")
        else:
            validation['checks']['package_assigned'] = False
            validation['status'] = 'FAIL'
            logger.warning(f"✗ Access package '{expected_access_package}' NOT assigned to {upn}")
        
        return validation
    
    def run_complete_validation(self, user_data: Dict, expected_groups: List[str], 
                                expected_package: str) -> Dict:
        """
        Run complete identity validation workflow.
        This is the main entry point for user provisioning validation.
        """
        upn = user_data.get('upn')
        
        result = {
            'user_principal_name': upn,
            'validation_timestamp': datetime.now().isoformat(),
            'validations': [],
            'overall_status': 'PENDING'
        }
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting identity validation for: {upn}")
        logger.info(f"{'='*60}")
        
        # Run all validations in sequence
        result['validations'].append(self.validate_user_existence(upn))
        result['validations'].append(
            self.validate_name_matching(upn, user_data.get('display_name'))
        )
        result['validations'].append(
            self.validate_group_membership(upn, expected_groups)
        )
        result['validations'].append(
            self.validate_access_package(upn, expected_package)
        )
        
        # Calculate overall status
        statuses = [v.get('status') for v in result['validations']]
        if all(s == 'PASS' for s in statuses):
            result['overall_status'] = 'PASS'
            logger.info(f"✓ All validations PASSED for {upn}")
        elif any(s == 'FAIL' for s in statuses):
            result['overall_status'] = 'FAIL'
            logger.error(f"✗ One or more validations FAILED for {upn}")
        else:
            result['overall_status'] = 'PARTIAL'
            logger.warning(f"⊘ Partial validation success for {upn}")
        
        logger.info(f"{'='*60}\n")
        
        self.validation_results.append(result)
        return result
    
    # Helper methods (simulation)
    def _get_user_groups(self, upn: str) -> List[str]:
        """Simulate retrieving user's group memberships."""
        if 'john.doe' in upn:
            return ['CES Profiler - Tool - SuccessFactors', 'CES Profiler - City - Pune']
        elif 'jane.smith' in upn:
            return ['CES Profiler - Tool - SuccessFactors', 'CES Profiler - City - Mumbai', 
                   'CES Profiler - Supplier - TechCorp']
        return []
    
    def _get_user_access_package(self, upn: str, package_name: str) -> Optional[Dict]:
        """Simulate retrieving user's access package assignment."""
        if 'john.doe' in upn and 'CES Profiler' in package_name:
            return {
                'status': 'Delivered',
                'delivery_date': '2026-04-10',
                'expires': '2027-04-10'
            }
        return None
    
    def generate_compliance_report(self) -> str:
        """
        Generate a formatted compliance report of all validations.
        Useful for audit and governance purposes.
        """
        report = "AZURE AD IDENTITY VALIDATION COMPLIANCE REPORT\n"
        report += f"Generated: {datetime.now().isoformat()}\n"
        report += f"Tenant: {self.tenant_id}\n"
        report += "=" * 70 + "\n\n"
        
        if not self.validation_results:
            report += "No validation results to report.\n"
            return report
        
        pass_count = sum(1 for r in self.validation_results if r['overall_status'] == 'PASS')
        fail_count = sum(1 for r in self.validation_results if r['overall_status'] == 'FAIL')
        partial_count = sum(1 for r in self.validation_results if r['overall_status'] == 'PARTIAL')
        
        report += f"SUMMARY:\n"
        report += f"  Total Users Validated: {len(self.validation_results)}\n"
        report += f"  ✓ Passed: {pass_count}\n"
        report += f"  ✗ Failed: {fail_count}\n"
        report += f"  ⊘ Partial: {partial_count}\n"
        report += f"  Compliance Rate: {(pass_count/len(self.validation_results)*100):.1f}%\n\n"
        
        report += "DETAILED RESULTS:\n"
        report += "-" * 70 + "\n"
        
        for result in self.validation_results:
            report += f"\nUser: {result['user_principal_name']}\n"
            report += f"Status: {result['overall_status']}\n"
            for validation in result['validations']:
                status_icon = "✓" if validation['status'] == 'PASS' else "✗" if validation['status'] == 'FAIL' else "⊘"
                report += f"  {status_icon} {validation['validation_name']}: {validation['status']}\n"
        
        return report


def main():
    """
    Demonstration of the Azure AD Identity Validator.
    This showcases real-world user provisioning and validation scenarios.
    """
    
    print("\n" + "="*70)
    print("AZURE AD USER PROVISIONING & VALIDATION PROJECT")
    print("="*70 + "\n")
    
    # Initialize validator
    validator = AzureADIdentityValidator(
        tenant_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        mock_mode=True
    )
    
    # Example 1: John Doe - Standard provisioning
    print("SCENARIO 1: Standard User Provisioning")
    print("-" * 70)
    john_data = {
        'user_id': 'user-001',
        'display_name': 'John Doe',
        'upn': 'john.doe@microsoft.com',
        'mail': 'john.doe@microsoft.com',
        'enabled': True,
        'invitation_state': 'Accepted'
    }
    validator.create_user_account(john_data)
    result1 = validator.run_complete_validation(
        user_data=john_data,
        expected_groups=['CES Profiler - Tool - SuccessFactors', 'CES Profiler - City - Pune'],
        expected_package='CES Profiler - Provisioning'
    )
    print(f"Validation Status: {result1['overall_status']}\n")
    
    # Example 2: Jane Smith - Multi-region with access package
    print("SCENARIO 2: Multi-Region User with Access Package")
    print("-" * 70)
    jane_data = {
        'user_id': 'user-002',
        'display_name': 'Jane Smith',
        'upn': 'jane.smith@microsoft.com',
        'mail': 'jane.smith@microsoft.com',
        'enabled': True,
        'invitation_state': 'Accepted'
    }
    validator.create_user_account(jane_data)
    result2 = validator.run_complete_validation(
        user_data=jane_data,
        expected_groups=['CES Profiler - Tool - SuccessFactors', 
                        'CES Profiler - City - Mumbai',
                        'CES Profiler - Supplier - TechCorp'],
        expected_package='CES Profiler - Supplier Package'
    )
    print(f"Validation Status: {result2['overall_status']}\n")
    
    # Generate compliance report
    print("\n" + "="*70)
    print("COMPLIANCE REPORT")
    print("="*70)
    report = validator.generate_compliance_report()
    print(report)
    
    # Save report to file
    with open('identity_compliance_report.txt', 'w') as f:
        f.write(report)
    logger.info("Compliance report saved to: identity_compliance_report.txt")
    
    # Export results as JSON (for integrations, dashboards)
    with open('validation_results.json', 'w') as f:
        json.dump([asdict(r) for r in validator.validation_results], f, indent=2, default=str)
    logger.info("Validation results exported to: validation_results.json")
    
    print("\n✓ Project execution completed successfully!")
    print("Files generated:")
    print("  - identity_audit_log.txt (audit trail)")
    print("  - identity_compliance_report.txt (compliance report)")
    print("  - validation_results.json (machine-readable results)")


if __name__ == "__main__":
    main()
