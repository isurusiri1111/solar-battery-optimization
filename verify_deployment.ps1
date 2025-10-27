# Deployment Verification Script
# Checks if all required files are present and configured correctly

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   DEPLOYMENT VERIFICATION" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$allGood = $true

# Check required files
Write-Host "Checking required files..." -ForegroundColor Yellow
Write-Host ""

$requiredFiles = @(
    "Procfile",
    "runtime.txt",
    "railway.json",
    ".gitignore",
    "requirements.txt",
    "api_server.py",
    "dashboard.html",
    "run.py"
)

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file - MISSING!" -ForegroundColor Red
        $allGood = $false
    }
}

Write-Host ""

# Check Procfile content
Write-Host "Checking Procfile configuration..." -ForegroundColor Yellow
if (Test-Path "Procfile") {
    $procfileContent = Get-Content "Procfile" -Raw
    if ($procfileContent -match 'uvicorn api_server:app.*--port \$PORT') {
        Write-Host "  ✓ Procfile is correctly configured" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Procfile may be incorrect" -ForegroundColor Red
        Write-Host "    Content: $procfileContent" -ForegroundColor Gray
        $allGood = $false
    }
}

Write-Host ""

# Check runtime.txt
Write-Host "Checking Python version..." -ForegroundColor Yellow
if (Test-Path "runtime.txt") {
    $runtime = Get-Content "runtime.txt" -Raw
    $runtime = $runtime.Trim()
    if ($runtime -eq "python-3.12.0") {
        Write-Host "  ✓ runtime.txt specifies python-3.12.0" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ runtime.txt contains: $runtime" -ForegroundColor Yellow
        Write-Host "    Expected: python-3.12.0" -ForegroundColor Gray
    }
}

Write-Host ""

# Check requirements.txt
Write-Host "Checking dependencies..." -ForegroundColor Yellow
if (Test-Path "requirements.txt") {
    $requirements = Get-Content "requirements.txt"
    $criticalPackages = @("tensorflow", "fastapi", "uvicorn", "pandas", "numpy")
    
    foreach ($package in $criticalPackages) {
        $found = $requirements | Where-Object { $_ -match "^$package" }
        if ($found) {
            Write-Host "  ✓ $package found" -ForegroundColor Green
        } else {
            Write-Host "  ✗ $package missing!" -ForegroundColor Red
            $allGood = $false
        }
    }
} else {
    Write-Host "  ✗ requirements.txt missing!" -ForegroundColor Red
    $allGood = $false
}

Write-Host ""

# Check directory structure
Write-Host "Checking directory structure..." -ForegroundColor Yellow
$requiredDirs = @("core", "continuous", "models", "data")

foreach ($dir in $requiredDirs) {
    if (Test-Path $dir -PathType Container) {
        Write-Host "  ✓ $dir/ folder exists" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $dir/ folder missing!" -ForegroundColor Red
        $allGood = $false
    }
}

Write-Host ""

# Check Git status
Write-Host "Checking Git configuration..." -ForegroundColor Yellow
if (Test-Path ".git") {
    Write-Host "  ✓ Git repository initialized" -ForegroundColor Green
    
    try {
        $remoteUrl = git remote get-url origin 2>&1
        if ($LASTEXITCODE -eq 0 -and $remoteUrl) {
            Write-Host "  ✓ GitHub remote configured: $remoteUrl" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ No GitHub remote configured yet" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ⚠ No GitHub remote configured yet" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⚠ Git not initialized (run: git init)" -ForegroundColor Yellow
}

Write-Host ""

# Check dashboard API URL
Write-Host "Checking dashboard configuration..." -ForegroundColor Yellow
if (Test-Path "dashboard.html") {
    $dashboard = Get-Content "dashboard.html" -Raw
    if ($dashboard -match 'const API_URL = ''([^'']+)''') {
        $apiUrl = $matches[1]
        if ($apiUrl -eq "http://localhost:8000") {
            Write-Host "  ⚠ Dashboard still points to localhost" -ForegroundColor Yellow
            Write-Host "    Update after Railway deployment!" -ForegroundColor Gray
        } elseif ($apiUrl -match "railway\.app") {
            Write-Host "  ✓ Dashboard configured for Railway: $apiUrl" -ForegroundColor Green
        } else {
            Write-Host "  ℹ Dashboard API URL: $apiUrl" -ForegroundColor Cyan
        }
    }
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan

if ($allGood) {
    Write-Host "   ✓ ALL CHECKS PASSED!" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Your project is ready for Railway deployment!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Run: .\setup_git.ps1 (to push to GitHub)" -ForegroundColor White
    Write-Host "2. Go to: https://railway.app" -ForegroundColor White
    Write-Host "3. Deploy from your GitHub repository" -ForegroundColor White
    Write-Host ""
    Write-Host "See DEPLOYMENT_GUIDE.md for detailed instructions!" -ForegroundColor Cyan
} else {
    Write-Host "   ✗ SOME CHECKS FAILED" -ForegroundColor Red
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Please fix the issues above before deploying." -ForegroundColor Yellow
}

Write-Host ""
pause
