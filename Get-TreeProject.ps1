# Get-ProjectTree.ps1
# PowerShell script to generate a clean project tree structure excluding .gitignore patterns

param(
    [string]$ProjectPath = "C:\Projects\task-python-orchestrator",
    [string]$OutputFile = "project_structure.md"
)

# Define exclusion patterns based on .gitignore
$ExclusionPatterns = @(
    # Python
    '__pycache__', '*.pyc', '*.pyo', '*.pyd', '*.so', '.Python',
    'build', 'develop-eggs', 'dist', 'downloads', 'eggs', '.eggs',
    'lib', 'lib64', 'parts', 'sdist', 'var', 'wheels', 'share',
    '*.egg-info', '.installed.cfg', '*.egg', 'MANIFEST',
    
    # PyInstaller
    '*.manifest', '*.spec',
    
    # Testing
    'htmlcov', '.tox', '.nox', '.coverage', '.coverage.*', '.cache',
    'nosetests.xml', 'coverage.xml', '*.cover', '*.py,cover',
    '.hypothesis', '.pytest_cache', 'cover',
    
    # Virtual Environments
    '.env', '.venv', 'env', 'venv', 'ENV', 'env.bak', 'venv.bak',
    '.conda', 'conda-meta',
    
    # IDEs and Editors
    '.vscode', '.idea', '*.swp', '*.swo', '*~', '.project',
    '.pydevproject', '.settings', '*.sublime-project', '*.sublime-workspace',
    '.spyderproject', '.spyproject', '.ropeproject',
    
    # OS Generated
    '.DS_Store', '.DS_Store?', '._*', '.Spotlight-V100', '.Trashes',
    'ehthumbs.db', 'Thumbs.db', 'desktop.ini', 'Desktop.ini',
    
    # Project-Specific Data
    'data', '*.db', '*.sqlite', '*.sqlite3', 'orchestrator.db',
    
    # Logs
    'logs', '*.log', '*.log.*', 'log',
    
    # Excel/CSV
    '*.xlsx', '*.xls', '*.csv', '*_data_*.xlsx', 'totango_*.xlsx',
    'citus_*.xlsx', 'monthly_report_*.xlsx',
    
    # Config with sensitive data
    '.env.local', '.env.*.local', 'config.ini', 'config.yaml',
    'config.yml', 'secrets.json', 'credentials.json',
    
    # Backup files
    '*.bak', '*.backup', '*.tmp', '*.temp',
    
    # Network/temp
    'downloads', 'temp', 'tmp',
    
    # Email configs
    'email_config.json', 'smtp_config.ini',
    
    # Certificates
    '*.pem', '*.key', '*.crt', '*.cert', '*.p12', '*.pfx',
    
    # Jupyter
    '.ipynb_checkpoints',
    
    # Flask
    'instance', '.webassets-cache',
    
    # Documentation builds
    'docs/_build', '/site',
    
    # Type checkers
    '.mypy_cache', '.dmypy.json', 'dmypy.json', '.pyre', '.pytype',
    'cython_debug',
    
    # Node.js
    'node_modules', 'npm-debug.log*', 'yarn-debug.log*', 'yarn-error.log*',
    
    # Package locks
    'Pipfile.lock', 'poetry.lock',
    
    # Environment files
    '.env.production', '.env.development', '.env.test',
    
    # PID files
    '*.pid', 'pids', '*.seed', '*.pid.lock',
    
    # Local development
    'local_config.py', 'local_settings.py', 'dev_config.py',
    
    # Task outputs
    'reports', 'output', 'exports',
    
    # macOS specific
    '.AppleDouble', '.LSOverride', 'Icon', '.DocumentRevisions-V100',
    '.fseventsd', '.TemporaryItems', '.VolumeIcon.icns',
    '.com.apple.timemachine.donotpresent',
    
    # Linux specific
    '.fuse_hidden*', '.directory', '.Trash-*', '.nfs*',
    
    # Archives
    '*.zip', '*.tar.gz', '*.rar', '*.7z',
    
    # Workspace files
    '*.code-workspace', '.history',
    
    # Cache directories
    '.npm', '.eslintcache', '.rpt2_cache', '.rts2_cache_cjs',
    '.rts2_cache_es', '.rts2_cache_umd',
    
    # REPL history
    '.node_repl_history',
    
    # Output files
    '*.tgz', '.yarn-integrity',
    
    # VSCode test
    '.vscode-test',
    
    # Custom project patterns
    'encrypted_credentials', '*.encrypted', 'task_outputs',
    'execution_logs', 'vpn_status.cache', 'email_queue', 'email_temp',
    '*.db.backup', 'database_backups', 'test_data', 'sample_data',
    'perf_logs', '*.perf', '*.lock', 'task_locks',
    '*_simulator.py', '*_demo.py', 'demo_*', 'simulation_*',
    
    # Additional custom exclusions
    '.claude', '*.txt', 'claude.md', 'docs', 'linven', '.git', '.windsurf'
)

# Function to check if a path should be excluded
function Test-ShouldExclude {
    param([string]$Path, [string]$Name)
    
    foreach ($pattern in $ExclusionPatterns) {
        # Handle exact matches
        if ($Name -eq $pattern) { return $true }
        
        # Handle wildcard patterns
        if ($pattern.Contains('*')) {
            if ($Name -like $pattern) { return $true }
        }
        
        # Handle directory patterns (check if current path contains the pattern)
        if ($Path -like "*\$pattern\*" -or $Path -like "*\$pattern" -or $Path -eq $pattern) {
            return $true
        }
        
        # Handle patterns that start with specific paths
        if ($pattern.StartsWith('/') -and $Path -like "*$($pattern.Substring(1))*") {
            return $true
        }
    }
    return $false
}

# Function to get file type indicator
function Get-FileIcon {
    param([string]$Extension, [bool]$IsContainer)
    
    if ($IsContainer) {
        return "[DIR]"
    }
    
    switch -Regex ($Extension) {
        '\.py$' { return "[PY] " }
        '\.md$' { return "[MD] " }
        '\.json$' { return "[JSON]" }
        '\.yml$|\.yaml$' { return "[YAML]" }
        '\.txt$' { return "[TXT]" }
        '\.html$' { return "[HTML]" }
        '\.js$' { return "[JS] " }
        '\.css$' { return "[CSS]" }
        '\.bat$|\.ps1$' { return "[SCRIPT]" }
        '\.toml$' { return "[TOML]" }
        '\.ini$' { return "[INI]" }
        '\.cfg$' { return "[CFG]" }
        '\.sql$' { return "[SQL]" }
        default { return "[FILE]" }
    }
}

# Function to generate tree structure
function Get-TreeStructure {
    param(
        [string]$Path,
        [string]$Prefix = "",
        [bool]$IsLast = $true,
        [int]$Level = 0
    )
    
    $items = @()
    
    try {
        if (-not (Test-Path $Path)) {
            Write-Warning "Path not found: $Path"
            return $items
        }
        
        # Get all items in current directory
        $allItems = Get-ChildItem -Path $Path -Force -ErrorAction SilentlyContinue | 
                    Where-Object { -not (Test-ShouldExclude -Path $_.FullName -Name $_.Name) } |
                    Sort-Object @{Expression = {$_.PSIsContainer}; Descending = $true}, Name
        
        if ($allItems) {
            # Inside Get-TreeStructure
            for ($i = 0; $i -lt $allItems.Count; $i++) {
                $item = $allItems[$i]
                # Always use pipe regardless of last item status
                $connector = "|-- "
                $newPrefix = "$Prefix|   "
                $icon = Get-FileIcon -Extension $item.Extension -IsContainer $item.PSIsContainer
                $line = "$Prefix$connector$icon $($item.Name)"
                $items += $line
                if ($item.PSIsContainer -and $Level -lt 10) {
                    $subItems = Get-TreeStructure -Path $item.FullName -Prefix $newPrefix -IsLast $false -Level ($Level + 1)
                    $items += $subItems
                }
            }

        }
    }
    catch {
        Write-Warning "Error processing $Path : $($_.Exception.Message)"
    }
    
    return $items
}

# Main execution
Write-Host "Generating project tree structure..." -ForegroundColor Green
Write-Host "Project Path: $ProjectPath" -ForegroundColor Cyan
Write-Host "Output File: $OutputFile" -ForegroundColor Cyan
Write-Host ""

# Check if project path exists
if (-not (Test-Path $ProjectPath)) {
    Write-Error "Project path does not exist: $ProjectPath"
    exit 1
}

# Generate the tree structure
$projectName = Split-Path $ProjectPath -Leaf
$treeLines = @()
$treeLines += "[ROOT] $projectName"

# Get the tree structure
$structure = Get-TreeStructure -Path $ProjectPath

# Combine all lines
$allLines = $treeLines + $structure

# Create markdown content
$markdownContent = @"
# Project Structure: $projectName

``````
$($allLines -join "`n")
``````

## Summary

- **Total Items Displayed**: $($structure.Count)
- **Project Root**: ``$ProjectPath``

"@

# Display to console
Write-Host "PROJECT STRUCTURE" -ForegroundColor Green
Write-Host ("=" * 50) -ForegroundColor Gray
$allLines | ForEach-Object { Write-Host $_ }
Write-Host ("=" * 50) -ForegroundColor Gray
Write-Host "Total items: $($structure.Count)" -ForegroundColor Yellow

# Save to markdown file
$outputPath = Join-Path $ProjectPath $OutputFile
try {
    $markdownContent | Out-File -FilePath $outputPath -Encoding UTF8
    Write-Host "Structure saved to: $outputPath" -ForegroundColor Green
}
catch {
    Write-Error "Failed to save file: $($_.Exception.Message)"
}

# Optional: Open the file
$openFile = Read-Host "Open the generated file? (y/N)"
if ($openFile -eq 'y' -or $openFile -eq 'Y') {
    try {
        Invoke-Item $outputPath
    }
    catch {
        Write-Warning "Could not open file automatically. File location: $outputPath"
    }
}

Write-Host "`nTree generation complete!" -ForegroundColor Green