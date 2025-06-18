# Get-ProjectTree.ps1
# PowerShell script to generate a clean project tree structure with proper exclusions

param(
    [string]$ProjectPath = "C:\Projects\task-python-orchestrator",
    [string]$OutputFile = "project_structure.md"
)

# Define exclusion patterns based on .gitignore
$ExclusionPatterns = @(
    # Git and IDE
    '.git', '.windsurf', '.vscode', '.idea', '.settings',
    
    # Python
    '__pycache__', 'build', 'develop-eggs', 'dist', 'downloads', 
    'eggs', '.eggs', 'lib', 'lib64', 'parts', 'sdist', 'var', 
    'wheels', 'share', '.Python',
    
    # Testing
    'htmlcov', '.tox', '.nox', '.cache', '.hypothesis', 
    '.pytest_cache', 'cover',
    
    # Virtual Environments
    '.env', '.venv', 'env', 'venv', 'ENV', 'env.bak', 'venv.bak',
    '.conda', 'conda-meta',
    
    # OS Generated
    '.DS_Store', '.Spotlight-V100', '.Trashes',
    
    # Project-Specific Data
    'data', 'logs', 'log',
    
    # Network/temp
    'downloads', 'temp', 'tmp',
    
    # Jupyter
    '.ipynb_checkpoints',
    
    # Flask
    'instance', '.webassets-cache',
    
    # Documentation builds
    '_build', 'site',
    
    # Type checkers
    '.mypy_cache', '.pyre', '.pytype', 'cython_debug',
    
    # Node.js
    'node_modules',
    
    # Cache directories
    '.npm', '.eslintcache',
    
    # Custom project patterns
    'encrypted_credentials', 'task_outputs', 'execution_logs',
    'database_backups', 'test_data', 'sample_data', 'perf_logs',
    'task_locks', 'email_queue', 'email_temp',
    
    # Additional custom exclusions
    '.claude', 'docs', 'linven'
)

# File extensions to exclude
$ExcludedExtensions = @(
    '*.pyc', '*.pyo', '*.pyd', '*.so', '*.egg-info', '*.egg',
    '*.manifest', '*.spec', '*.coverage', '*.cover', '*.log',
    '*.db', '*.sqlite', '*.sqlite3', '*.xlsx', '*.xls', '*.csv',
    '*.bak', '*.backup', '*.tmp', '*.temp', '*.pem', '*.key',
    '*.crt', '*.cert', '*.p12', '*.pfx', '*.zip', '*.tar.gz',
    '*.rar', '*.7z', '*.pid', '*.lock', '*.encrypted', '*.perf',
    'Thumbs.db', 'ehthumbs.db', 'Desktop.ini', 'desktop.ini',
    '*.txt', '*.md'
)

# Exception: Keep these specific files even if they match excluded extensions
$KeepFiles = @(
    'requirements.txt', 'README.md', '.gitignore', 'pyproject.toml',
    '.pre-commit-config.yaml'
)

# Function to check if a directory should be excluded
function Test-ShouldExcludeDirectory {
    param([string]$DirectoryName, [string]$FullPath)
    
    # Check against exclusion patterns
    foreach ($pattern in $ExclusionPatterns) {
        if ($DirectoryName -eq $pattern) {
            return $true
        }
        if ($pattern.Contains('*') -and $DirectoryName -like $pattern) {
            return $true
        }
    }
    
    return $false
}

# Function to check if a file should be excluded
function Test-ShouldExcludeFile {
    param([string]$FileName, [string]$FullPath)
    
    # Check if file is in keep list first
    if ($KeepFiles -contains $FileName) {
        return $false
    }
    
    # Check against excluded extensions
    foreach ($pattern in $ExcludedExtensions) {
        if ($FileName -like $pattern) {
            return $true
        }
    }
    
    return $false
}

# Function to get file type prefix
function Get-FileTypePrefix {
    param([string]$Extension, [bool]$IsDirectory)
    
    if ($IsDirectory) {
        return ""
    }
    
    switch -Regex ($Extension) {
        '\.py$' { return "[PY]   " }
        '\.md$' { return "[MD]   " }
        '\.json$' { return "[JSON] " }
        '\.ya?ml$' { return "[YAML] " }
        '\.html$' { return "[HTML] " }
        '\.js$' { return "[JS]   " }
        '\.css$' { return "[CSS]  " }
        '\.ps1$|\.bat$' { return "[SCRIPT]" }
        '\.toml$' { return "[TOML] " }
        '\.txt$' { return "[TXT]  " }
        default { return "[FILE] " }
    }
}

# Main tree generation function
function Get-CustomTree {
    param(
        [string]$Path,
        [string]$Prefix = "",
        [bool]$IsLast = $true,
        [int]$Depth = 0
    )
    
    $result = @()
    
    try {
        if (-not (Test-Path $Path)) {
            return $result
        }
        
        # Get directories first, then files - but exclude before processing
        $directories = Get-ChildItem -Path $Path -Directory -Force -ErrorAction SilentlyContinue | 
                      Where-Object { -not (Test-ShouldExcludeDirectory -DirectoryName $_.Name -FullPath $_.FullName) } |
                      Sort-Object Name
        
        $files = Get-ChildItem -Path $Path -File -Force -ErrorAction SilentlyContinue |
                 Where-Object { -not (Test-ShouldExcludeFile -FileName $_.Name -FullPath $_.FullName) } |
                 Sort-Object Name
        
        # Combine and process all items
        $allItems = @()
        $allItems += $directories
        $allItems += $files
        
        if ($allItems.Count -eq 0) {
            return $result
        }
        
        for ($i = 0; $i -lt $allItems.Count; $i++) {
            $item = $allItems[$i]
            $isLastItem = ($i -eq ($allItems.Count - 1))
            
            # Build tree characters using ASCII
            if ($isLastItem) {
                $connector = "+-- "
                $newPrefix = "$Prefix    "
            } else {
                $connector = "+-- "
                $newPrefix = "$Prefix|   "
            }
            
            # Get file type prefix
            $typePrefix = Get-FileTypePrefix -Extension $item.Extension -IsDirectory $item.PSIsContainer
            
            # Build the line
            $line = "$Prefix$connector$typePrefix$($item.Name)"
            $result += $line
            
            # Recurse into directories (they've already been filtered)
            if ($item.PSIsContainer -and $Depth -lt 15) {
                $subItems = Get-CustomTree -Path $item.FullName -Prefix $newPrefix -IsLast $isLastItem -Depth ($Depth + 1)
                $result += $subItems
            }
        }
    }
    catch {
        Write-Warning "Error processing $Path : $($_.Exception.Message)"
    }
    
    return $result
}

# Main execution
Write-Host "Generating project tree structure..." -ForegroundColor Green
Write-Host "Project Path: $ProjectPath" -ForegroundColor Cyan
Write-Host "Output File: $OutputFile" -ForegroundColor Cyan
Write-Host ""

# Validate project path
if (-not (Test-Path $ProjectPath)) {
    Write-Error "Project path does not exist: $ProjectPath"
    exit 1
}

# Generate the tree structure
Write-Host "Building tree structure..." -ForegroundColor Yellow
$projectName = Split-Path $ProjectPath -Leaf

# Get the tree structure starting from project root
$treeLines = Get-CustomTree -Path $ProjectPath

# Prepare the root line
$rootLine = "$projectName"
$allLines = @($rootLine) + $treeLines

# Count non-empty items
$itemCount = $treeLines.Count

# Create markdown content
$markdownContent = @"
# Project Structure: $projectName

``````
$($allLines -join "`n")
``````

## Summary

- **Total Items Displayed**: $itemCount
- **Project Root**: ``$ProjectPath``

"@

# Display to console
Write-Host ""
Write-Host "PROJECT STRUCTURE" -ForegroundColor Green
Write-Host ("=" * 60) -ForegroundColor Gray
$allLines | ForEach-Object { Write-Host $_ }
Write-Host ("=" * 60) -ForegroundColor Gray
Write-Host "Total items: $itemCount" -ForegroundColor Yellow
Write-Host ""

# Save to markdown file
$outputPath = Join-Path $ProjectPath $OutputFile
try {
    $markdownContent | Out-File -FilePath $outputPath -Encoding UTF8
    Write-Host "Structure saved to: $outputPath" -ForegroundColor Green
}
catch {
    Write-Error "Failed to save file: $($_.Exception.Message)"
    exit 1
}

# Optional: Open the file
$openFile = Read-Host "Open the generated file? (y/N)"
if ($openFile -eq 'y' -or $openFile -eq 'Y') {
    try {
        Invoke-Item $outputPath
        Write-Host "✓ File opened successfully" -ForegroundColor Green
    }
    catch {
        Write-Warning "Could not open file automatically. File location: $outputPath"
    }
}

Write-Host ""
Write-Host "Tree generation complete!" -ForegroundColor Green
Write-Host "Excluded patterns applied: Git dirs, cache files, data dirs, logs, etc." -ForegroundColor Gray