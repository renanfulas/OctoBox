param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Encrypt", "Decrypt")]
    [string]$Mode,

    [Parameter(Mandatory = $true)]
    [string]$InputPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath,

    [Parameter(Mandatory = $true)]
    [string]$Passphrase
)

$ErrorActionPreference = "Stop"

function New-RandomBytes([int]$Length) {
    $bytes = New-Object byte[] $Length
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    }
    finally {
        $rng.Dispose()
    }
    return $bytes
}

function Get-KeyMaterial([string]$Passphrase, [byte[]]$Salt) {
    $pbkdf = [System.Security.Cryptography.Rfc2898DeriveBytes]::new(
        $Passphrase,
        $Salt,
        310000,
        [System.Security.Cryptography.HashAlgorithmName]::SHA256
    )
    try {
        return $pbkdf.GetBytes(64)
    }
    finally {
        $pbkdf.Dispose()
    }
}

function Compare-BytesConstantTime([byte[]]$Left, [byte[]]$Right) {
    if ($Left.Length -ne $Right.Length) {
        return $false
    }
    $diff = 0
    for ($i = 0; $i -lt $Left.Length; $i++) {
        $diff = $diff -bor ($Left[$i] -bxor $Right[$i])
    }
    return $diff -eq 0
}

if ($Mode -eq "Encrypt") {
    $plain = [System.IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $InputPath))
    $salt = New-RandomBytes 16
    $iv = New-RandomBytes 16
    $material = Get-KeyMaterial $Passphrase $salt
    $encKey = $material[0..31]
    $macKey = $material[32..63]

    $aes = [System.Security.Cryptography.Aes]::Create()
    try {
        $aes.Mode = [System.Security.Cryptography.CipherMode]::CBC
        $aes.Padding = [System.Security.Cryptography.PaddingMode]::PKCS7
        $aes.Key = $encKey
        $aes.IV = $iv
        $encryptor = $aes.CreateEncryptor()
        $cipher = $encryptor.TransformFinalBlock($plain, 0, $plain.Length)
    }
    finally {
        $aes.Dispose()
    }

    $magic = [System.Text.Encoding]::ASCII.GetBytes("OCTOENV1")
    $payload = $magic + $salt + $iv + $cipher
    $hmac = [System.Security.Cryptography.HMACSHA256]::new($macKey)
    try {
        $tag = $hmac.ComputeHash($payload)
    }
    finally {
        $hmac.Dispose()
    }
    [System.IO.File]::WriteAllBytes($OutputPath, $payload + $tag)
    Write-Output "Encrypted backup written to $OutputPath"
    exit 0
}

$encrypted = [System.IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $InputPath))
if ($encrypted.Length -lt 88) {
    throw "Encrypted file is too short."
}

$magic = [System.Text.Encoding]::ASCII.GetString($encrypted[0..7])
if ($magic -ne "OCTOENV1") {
    throw "Invalid encrypted backup header."
}

$salt = $encrypted[8..23]
$iv = $encrypted[24..39]
$cipherEnd = $encrypted.Length - 33
$cipher = $encrypted[40..$cipherEnd]
$tag = $encrypted[($encrypted.Length - 32)..($encrypted.Length - 1)]
$payload = $encrypted[0..$cipherEnd]

$material = Get-KeyMaterial $Passphrase $salt
$encKey = $material[0..31]
$macKey = $material[32..63]
$hmac = [System.Security.Cryptography.HMACSHA256]::new($macKey)
try {
    $expectedTag = $hmac.ComputeHash($payload)
}
finally {
    $hmac.Dispose()
}

if (-not (Compare-BytesConstantTime $tag $expectedTag)) {
    throw "Invalid passphrase or corrupted encrypted backup."
}

$aes = [System.Security.Cryptography.Aes]::Create()
try {
    $aes.Mode = [System.Security.Cryptography.CipherMode]::CBC
    $aes.Padding = [System.Security.Cryptography.PaddingMode]::PKCS7
    $aes.Key = $encKey
    $aes.IV = $iv
    $decryptor = $aes.CreateDecryptor()
    $plain = $decryptor.TransformFinalBlock($cipher, 0, $cipher.Length)
}
finally {
    $aes.Dispose()
}

[System.IO.File]::WriteAllBytes($OutputPath, $plain)
Write-Output "Decrypted backup written to $OutputPath"
