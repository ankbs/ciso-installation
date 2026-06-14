# Requires -Version 7.2

<#
.SYNOPSIS
    REST-based M365 Security & GRC Compliance Collector. (Community Edition)
.DESCRIPTION
    Connects to the Microsoft Graph API directly via HTTPS REST requests (v1.0 and beta)
    to audit Entra ID security defaults and tenant configurations. Submits the findings
    as compliance issues to the CISO Assistant GRC API.
.PARAMETER TenantId
    The M365 Tenant ID (Directory ID).
.PARAMETER ClientId
    The App Registration (Client) ID.
.PARAMETER ClientSecret
    The App Registration Client Secret (passed as SecureString for security).
.PARAMETER CisoApiUrl
    The base URL of the target CISO Assistant instance.
.PARAMETER CisoApiToken
    The API token (PAT) for the CISO Assistant instance (passed as SecureString).
.EXAMPLE
    $Secret = Read-Host -AsSecureString "Enter Client Secret"
    $Token = Read-Host -AsSecureString "Enter CISO Token"
    Invoke-M365ComplianceAudit -TenantId "1111-1111-1111" -ClientId "0000-0000" -ClientSecret $Secret -CisoApiUrl "https://ciso.deinedomain.de" -CisoApiToken $Token
#>

function Invoke-M365ComplianceAudit {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param(
        [Parameter(Mandatory = $true)]
        [string]$TenantId,

        [Parameter(Mandatory = $true)]
        [string]$ClientId,

        [Parameter(Mandatory = $true)]
        [System.Security.SecureString]$ClientSecret,

        [Parameter(Mandatory = $true)]
        [ValidatePattern('^https?://')]
        [string]$CisoApiUrl,

        [Parameter(Mandatory = $true)]
        [System.Security.SecureString]$CisoApiToken
    )

    process {
        # 1. Decrypt credentials securely in memory
        Write-Verbose "Decrypting credentials in memory securely..."
        $PlainSecret = [System.Net.NetworkCredential]::new("", $ClientSecret).Password
        $PlainCisoToken = [System.Net.NetworkCredential]::new("", $CisoApiToken).Password

        # 2. Authenticate against Microsoft Graph API using Client Credentials flow
        $TokenUrl = "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token"
        $Body = @{
            client_id     = $ClientId
            scope         = "https://graph.microsoft.com/.default"
            client_secret = $PlainSecret
            grant_type    = "client_credentials"
        }

        Write-Verbose "Requesting Microsoft Graph access token..."
        $GraphToken = $null
        try {
            $TokenResponse = Invoke-RestMethod -Uri $TokenUrl -Method Post -Body $Body -ContentType "application/x-www-form-urlencoded"
            $GraphToken = $TokenResponse.access_token
            Write-Verbose "Successfully authenticated to Microsoft Graph API."
        }
        catch {
            Write-Error "Failed to authenticate to Microsoft Graph: $($_.Exception.Message)"
            return
        }

        $Headers = @{
            "Authorization" = "Bearer $GraphToken"
            "Accept"        = "application/json"
        }

        # 3. Retrieve Tenant Info (Graph v1.0)
        $OrgUrl = "https://graph.microsoft.com/v1.0/organization"
        Write-Verbose "Fetching organization details..."
        $OrgName = "Unknown M365 Tenant"
        try {
            $OrgResponse = Invoke-RestMethod -Uri $OrgUrl -Method Get -Headers $Headers
            if ($OrgResponse.value) {
                $OrgName = $OrgResponse.value[0].displayName
                Write-Verbose "Auditing tenant: $OrgName"
            }
        }
        catch {
            Write-Warning "Could not fetch tenant organization details: $($_.Exception.Message)"
        }

        # 4. Audit Security Defaults (Graph Beta)
        $DefaultsUrl = "https://graph.microsoft.com/beta/policies/securityDefaults"
        Write-Verbose "Auditing Security Defaults setting..."
        $SecurityDefaultsEnabled = $false
        try {
            $DefaultsResponse = Invoke-RestMethod -Uri $DefaultsUrl -Method Get -Headers $Headers
            $SecurityDefaultsEnabled = $DefaultsResponse.isEnabled
            Write-Verbose "Security Defaults Enabled status: $SecurityDefaultsEnabled"
        }
        catch {
            Write-Warning "Could not fetch Security Defaults configuration: $($_.Exception.Message)"
        }

        # 5. Build GRC Finding Payload
        $FindingTitle = "Security Defaults Disabled ($OrgName)"
        $FindingSeverity = "high"
        $FindingDescription = "Microsoft Security Defaults sind im Tenant '$OrgName' deaktiviert. Dies erhoeht das Risiko von Identitaetsdiebstahl erheblich, da Standard-MFA-Richtlinien nicht erzwungen werden."
        $FindingStatus = "open"

        if ($SecurityDefaultsEnabled) {
            $FindingTitle = "Security Defaults Enabled ($OrgName)"
            $FindingSeverity = "info"
            $FindingDescription = "Microsoft Security Defaults sind im Tenant '$OrgName' aktiviert. Grundlegender Identitaetsschutz wird erzwungen."
            $FindingStatus = "closed"
        }

        $Payload = @{
            title       = $FindingTitle
            severity    = $FindingSeverity
            description = $FindingDescription
            reference   = "M365-SEC-001"
            status      = $FindingStatus
        }

        # 6. Submit finding to CISO Assistant GRC API
        $TargetUrl = "$($CisoApiUrl.TrimEnd('/'))/api/v1/findings/"
        $CisoHeaders = @{
            "Authorization" = "Token $PlainCisoToken"
            "Accept"        = "application/json"
        }

        if ($PSCmdlet.ShouldProcess("Tenant $OrgName (SecurityDefaults: $SecurityDefaultsEnabled)", "Submit finding to CISO Assistant at $TargetUrl")) {
            try {
                $JsonPayload = ConvertTo-Json -InputObject $Payload -Depth 5 -Compress
                $Response = Invoke-RestMethod -Uri $TargetUrl -Method Post -Headers $CisoHeaders -Body $JsonPayload -ContentType "application/json"
                Write-Verbose "Finding submitted successfully. Finding ID: $($Response.id)"
                return $Response
            }
            catch {
                $ErrorMessage = $_.Exception.Message
                if ($_.Exception.Response) {
                    $Reader = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
                    $ApiError = $Reader.ReadToEnd()
                    $ErrorMessage = "$ErrorMessage - Details: $ApiError"
                }
                Write-Error "Failed to submit finding to CISO Assistant: $ErrorMessage"
                return $null
            }
        }
    }
}
