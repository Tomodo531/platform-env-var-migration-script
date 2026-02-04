# Upsun Environment Variables Migration Script

This Python script helps you migrate environment variables from one Upsun/Platform.sh site to another by generating the necessary `variable:create` commands.

## Features

- Extracts all environment variables from a source environment
- Gets detailed information about each variable (sensitivity, visibility, JSON format, etc.)
- Generates ready-to-use `upsun variable:create` commands
- Handles secret values by using `<SECRET_VALUE>` placeholder
- Preserves variable properties (JSON, sensitive, build/runtime visibility)

## Prerequisites

- Python 3.6 or higher
- Upsun CLI installed and authenticated
- Access to both source and target projects

## Installation

1. Make the script executable:
```bash
chmod +x migrate_upsun_vars.py
```

## Usage

### Basic Usage

```bash
python3 migrate_upsun_vars.py \
  --source-env develop \
  --source-project ytgmykafpouz4 \
  --target-env production \
  --target-project abc123xyz456
```

### Save to File

```bash
python3 migrate_upsun_vars.py \
  --source-env develop \
  --source-project ytgmykafpouz4 \
  --target-env production \
  --target-project abc123xyz456 \
  --output migration_commands.sh
```

### Arguments

- `--source-env` or `-se`: Source environment name (e.g., `develop`)
- `--source-project` or `-sp`: Source project ID (e.g., `ytgmykafpouz4`)
- `--target-env` or `-te`: Target environment name (e.g., `production`)
- `--target-project` or `-tp`: Target project ID
- `--output` or `-o`: (Optional) Output file for the generated commands
- `--skip-inherited`: (Optional) Skip variables that are inherited from parent environments

## Example

Using your specific example:

```bash
python3 migrate_upsun_vars.py \
  -se develop \
  -sp ytgmykafpouz4 \
  -te production \
  -tp newproject123 \
  -o variables_migration.sh
```

This will:
1. Fetch all variables from the `develop` environment of project `ytgmykafpouz4`
2. Get detailed information for each variable
3. Generate `upsun variable:create` commands for the `production` environment of `newproject123`
4. Save the commands to `variables_migration.sh`

### Skip Inherited Variables

If you want to skip variables that are inherited from parent environments:

```bash
python3 migrate_upsun_vars.py \
  -se develop \
  -sp ytgmykafpouz4 \
  -te production \
  -tp newproject123 \
  --skip-inherited \
  -o variables_migration.sh
```

## After Running the Script

1. Review the generated commands in the output file
2. **Replace all `<SECRET_VALUE>` placeholders** with actual secret values
3. Make the output file executable: `chmod +x variables_migration.sh`
4. Run the commands: `./variables_migration.sh`

Or run commands individually if you prefer more control.

## Notes

- Secret/sensitive variables cannot be read, so their values are replaced with `<SECRET_VALUE>`
- You must manually replace these placeholders before executing the commands
- The script preserves all variable properties including:
  - `is_json`: Whether the value is JSON formatted
  - `is_sensitive`: Whether the variable contains sensitive data
  - `visible_build`: Visibility during build phase
  - `visible_runtime`: Visibility during runtime
  - `is_enabled`: Whether the variable is enabled
  - `is_inheritable`: Whether child environments can inherit this variable
  - `level`: Variable level (environment, project, etc.)
- Progress messages are printed to stderr, so you can redirect stdout to a file
- Use `--skip-inherited` to exclude variables inherited from parent environments

## Troubleshooting

If you encounter authentication issues:
```bash
upsun auth:login
```

If you need to verify your project IDs:
```bash
upsun projects
```

To verify environment names:
```bash
upsun environments -p YOUR_PROJECT_ID
```
