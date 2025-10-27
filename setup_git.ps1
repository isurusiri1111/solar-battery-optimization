# Git Setup and GitHub Push Script
# This script helps you set up Git and push to GitHub

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   GIT SETUP & GITHUB PUSH HELPER" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Git is installed
Write-Host "Step 1: Checking Git installation..." -ForegroundColor Yellow
try {
    $gitVersion = git --version
    Write-Host "✓ Git is installed: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Git is NOT installed!" -ForegroundColor Red
    Write-Host "Please install Git from: https://git-scm.com/download/win" -ForegroundColor Yellow
    Write-Host "After installation, restart PowerShell and run this script again." -ForegroundColor Yellow
    pause
    exit
}

Write-Host ""

# Check if already a Git repository
if (Test-Path .git) {
    Write-Host "✓ Git repository already initialized" -ForegroundColor Green
} else {
    Write-Host "Step 2: Initializing Git repository..." -ForegroundColor Yellow
    git init
    Write-Host "✓ Git repository initialized" -ForegroundColor Green
}

Write-Host ""

# Configure Git user (if not configured)
Write-Host "Step 3: Checking Git configuration..." -ForegroundColor Yellow
$gitUser = git config --global user.name
$gitEmail = git config --global user.email

if (-not $gitUser) {
    Write-Host "Git username not configured." -ForegroundColor Yellow
    $name = Read-Host "Enter your name (e.g., John Smith)"
    git config --global user.name "$name"
    Write-Host "✓ Git username set to: $name" -ForegroundColor Green
} else {
    Write-Host "✓ Git username: $gitUser" -ForegroundColor Green
}

if (-not $gitEmail) {
    Write-Host "Git email not configured." -ForegroundColor Yellow
    $email = Read-Host "Enter your email"
    git config --global user.email "$email"
    Write-Host "✓ Git email set to: $email" -ForegroundColor Green
} else {
    Write-Host "✓ Git email: $gitEmail" -ForegroundColor Green
}

Write-Host ""

# Add all files
Write-Host "Step 4: Adding files to Git..." -ForegroundColor Yellow
git add .
Write-Host "✓ All files staged" -ForegroundColor Green

Write-Host ""

# Show status
Write-Host "Files ready to commit:" -ForegroundColor Cyan
git status --short

Write-Host ""

# Commit
Write-Host "Step 5: Creating commit..." -ForegroundColor Yellow
$commitMessage = Read-Host "Enter commit message (or press Enter for default)"
if (-not $commitMessage) {
    $commitMessage = "Initial commit - Ready for Railway deployment"
}
git commit -m "$commitMessage"
Write-Host "✓ Commit created" -ForegroundColor Green

Write-Host ""

# Check if remote exists
$remoteUrl = git remote get-url origin 2>$null
if ($remoteUrl) {
    Write-Host "✓ GitHub remote already configured: $remoteUrl" -ForegroundColor Green
    Write-Host ""
    Write-Host "Step 6: Pushing to GitHub..." -ForegroundColor Yellow
    git push -u origin main
    Write-Host "✓ Code pushed to GitHub!" -ForegroundColor Green
} else {
    Write-Host "Step 6: Configure GitHub remote..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please provide your GitHub repository URL." -ForegroundColor Cyan
    Write-Host "Example: https://github.com/YOUR_USERNAME/solar-battery-optimization.git" -ForegroundColor Gray
    Write-Host ""
    $repoUrl = Read-Host "GitHub repository URL"
    
    if ($repoUrl) {
        git remote add origin $repoUrl
        git branch -M main
        Write-Host "✓ Remote configured" -ForegroundColor Green
        Write-Host ""
        Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
        Write-Host "You may be prompted to login to GitHub..." -ForegroundColor Cyan
        git push -u origin main
        Write-Host "✓ Code pushed to GitHub!" -ForegroundColor Green
    } else {
        Write-Host "✗ No URL provided. Skipping push." -ForegroundColor Red
        Write-Host "You can push later with: git push -u origin main" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   SETUP COMPLETE!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Go to Railway: https://railway.app" -ForegroundColor White
Write-Host "2. Login with GitHub" -ForegroundColor White
Write-Host "3. Click 'New Project' → 'Deploy from GitHub repo'" -ForegroundColor White
Write-Host "4. Select your repository" -ForegroundColor White
Write-Host "5. Wait for deployment to complete" -ForegroundColor White
Write-Host "6. Generate domain in Settings → Networking" -ForegroundColor White
Write-Host ""
Write-Host "See DEPLOYMENT_GUIDE.md for detailed instructions!" -ForegroundColor Cyan
Write-Host ""
pause
