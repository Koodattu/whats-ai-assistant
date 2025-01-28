# PowerShell Script to Read and Format Python Files for LLM Input
# Navigate to the directory containing this script and run it.

# Get all .py files in the current directory
$pythonFiles = Get-ChildItem -Path . -Filter *.py

# Initialize an empty string to store formatted content
$formattedContent = ""

# Iterate through each .py file
foreach ($file in $pythonFiles) {
    # Read the content of the file
    $fileContent = Get-Content -Path $file.FullName -Raw
    
    # Append a formatted header and the file content to the result
    $formattedContent += "`n# Start of File: $($file.Name)`n"
    $formattedContent += $fileContent
    $formattedContent += "`n# End of File: $($file.Name)`n"
}

# Remove leading/trailing whitespace and ensure clipboard compatibility
$formattedContent = $formattedContent.Trim()

# Copy the formatted content to the clipboard
Set-Clipboard -Value $formattedContent

# Output success message
Write-Host "Python files' content has been formatted and copied to the clipboard."
