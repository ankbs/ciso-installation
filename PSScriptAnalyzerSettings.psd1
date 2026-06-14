@{
    # PSScriptAnalyzer Settings for M365 Security & Compliance Coding
    # Target: Quality, Security, and Code Cleanliness

    # Rules to include in the analysis
    IncludeRules = @(
        'PSAvoidDefaultValueSwitchParameter',
        'PSAvoidUsingEmptyCatchBlock',
        'PSAvoidUsingCmdletAliases',
        'PSAvoidUsingPlainTextForPassword',
        'PSAvoidUsingUsernameAndPasswordParams',
        'PSUseShouldProcessForStateChangingFunctions',
        'PSUseApprovedVerbs',
        'PSUseDeclaredVarsMoreThanAssignments',
        'PSUseConsistentWhitespace',
        'PSUseConsistentIndentation',
        'PSPossibleIncorrectUsageOfAssignmentOperator',
        'PSAvoidUsingWriteHost'
    )

    ExcludeRules = @()

    # Rule Configuration
    Rules = @{
        # Enforce 4 spaces for indentation
        PSUseConsistentIndentation = @{
            Enable = $true
            IndentationSize = 4
        }
        # Enforce approved verbs only
        PSUseApprovedVerbs = @{
            Enable = $true
        }
    }
}
