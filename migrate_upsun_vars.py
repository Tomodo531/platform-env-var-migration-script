#!/usr/bin/env python3
"""
Upsun Environment Variables Migration Script

This script extracts environment variables from a source Upsun environment
and generates commands to recreate them on a target environment.
"""

import subprocess
import csv
import io
import sys
import argparse


class colors:
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    WHITE = '\033[0m'



def run_command(command):
    """Execute a shell command and return the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        if e.returncode == 1 and e.stderr.startswith('Variable not found'):
            return None
        
        print(f"{colors.FAIL}Error running command: {command}{colors.WHITE}", file=sys.stderr)
        print(f"{colors.FAIL}Error: {e.stderr}{colors.WHITE}", file=sys.stderr)
        sys.exit(1)


def get_variable_list(environment, project):
    """Get list of all variables from the source environment."""
    command = f"upsun variable:list -e {environment} -p {project} --format csv"
    print(f"Fetching variable list...", file=sys.stderr)
    output = run_command(command)
    
    # Parse CSV output
    reader = csv.DictReader(io.StringIO(output))
    variables = list(reader)
    
    return variables


def get_variable_details(environment, project, var_name):
    """Get detailed information about a specific variable."""
    command = f"upsun variable:get -e {environment} -p {project} {var_name} --format csv"
    print(f"Fetching details for {colors.GREEN}{var_name}{colors.WHITE} from {colors.GREEN}{project}{colors.WHITE} ", file=sys.stderr)
    output = run_command(command)
    
    # Parse CSV output - format is Property,Value
    if output is None:
        return output
    
    reader = csv.DictReader(io.StringIO(output))
    rows = list(reader)
    
    # Convert from list of {Property: X, Value: Y} to single dict {X: Y}
    details = {}
    for row in rows:
        prop = row.get('Property', '')
        value = row.get('Value', '')
        if prop:
            details[prop] = value
    
    return details if details else None


def generate_create_command(var_details, source_env, source_project, source_app, target_env, target_project):
    """Generate the upsun variable:create command based on variable details."""
    # Extract variable information
    name = var_details.get('name', '')
    value = var_details.get('value', '')
    is_json = var_details.get('is_json', 'false').lower() == 'true'
    is_sensitive = var_details.get('is_sensitive', 'false').lower() == 'true'
    visible_build = var_details.get('visible_build', 'true').lower() == 'true'
    visible_runtime = var_details.get('visible_runtime', 'true').lower() == 'true'
    is_enabled = var_details.get('is_enabled', 'true').lower() == 'true'
    is_inheritable = var_details.get('is_inheritable', 'false').lower() == 'true'
    level = var_details.get('level', 'environment')
    
    # Build the command
    command_parts = [
        f"upsun variable:create",
        f"--no-wait "
        f"-p {target_project}"
    ]
    
    # If value is empty or sensitive, use placeholder
    if not value or is_sensitive:
        # Remove any prefix ending with ':' from name if present
        if ':' in name:
            name_without_prefix = name.split(':', 1)[1]
            
        value = run_command(f"upsun ssh -e {source_env} -p {source_project} --app {source_app} -- 'echo ${name_without_prefix}'")
        
    if get_variable_details(target_env, target_project, name) is not None:
        command_parts.append(f"--update")
    
    # Add level flag (environment, project, etc.)
    if level:
        command_parts.append(f"--level {level}")
    
    # Add environment flag if level is not project
    if level != 'project':
        command_parts.append(f"-e {target_env}")
    
    # Add flags based on properties
    if is_json:
        command_parts.append("--json true")
    else:
        command_parts.append("--json false")
    
    if is_sensitive:
        command_parts.append("--sensitive true")
    else:
        command_parts.append("--sensitive false")
    
    if visible_build:
        command_parts.append("--visible-build true")
    else:
        command_parts.append("--visible-build false")
    
    if visible_runtime:
        command_parts.append("--visible-runtime true")
    else:
        command_parts.append("--visible-runtime false")
    
    if not is_enabled:
        command_parts.append("--enabled false")
    
    if is_inheritable:
        command_parts.append("--inheritable true")
    
    # Add name and value (escape value if needed)
    # Escape single quotes in value
    escaped_value = value.replace("'", "'\\''").strip()
    command_parts.append(f"--name '{name}'")
    command_parts.append(f"--value '{escaped_value}'")
    
    return ' '.join(command_parts), is_sensitive


def main():
    parser = argparse.ArgumentParser(
        description='Migrate Upsun environment variables between sites'
    )
    parser.add_argument(
        '--source-env', '-se',
        required=True,
        help='Source environment name'
    )
    parser.add_argument(
        '--source-project', '-sp',
        required=True,
        help='Source project ID'
    )
    parser.add_argument(
        '--source-app',
        required=True,
        help='The source app of the project'
    )
    parser.add_argument(
        '--target-env', '-te',
        required=True,
        help='Target environment name'
    )
    parser.add_argument(
        '--target-project', '-tp',
        required=True,
        help='Target project ID'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output file for commands (default: stdout)'
    )
    parser.add_argument(
        '--skip-inherited',
        action='store_true',
        help='Skip variables that are inherited from parent environments'
    )
    
    args = parser.parse_args()
    
    # Get list of all variables
    variables = get_variable_list(args.source_env, args.source_project)
    
    print(f"Found {len(variables)} variables", file=sys.stderr)
    print("", file=sys.stderr)
    
    # Generate commands
    sensitive_commands = []
    commands = []
    skipped = 0
    
    for var in variables:
        var_name = var.get('Name')
        if not var_name:
            continue
        
        # Get detailed information
        details = get_variable_details(args.source_env, args.source_project, var_name)
        
        if details is None:
            print(f"Variable not found or could not retrieve details: {var_name}", file=sys.stderr)
            continue
        
        if details:
            # Check if we should skip inherited variables
            is_inherited = details.get('inherited', 'false').lower() == 'true'
            if args.skip_inherited and is_inherited:
                print(f"{colors.WARNING}Skipping inherited variable: {var_name}{colors.WHITE}", file=sys.stderr)
                skipped += 1
                continue
            
            # Generate create command
            command, is_sensitive = generate_create_command(details, args.source_env, args.source_project, args.source_app, args.target_env, args.target_project)
            
            if is_sensitive:
                sensitive_commands.append(command)
            else:
                commands.append(command)
    
    # Output commands
    output_content = "#!/bin/bash\n\n"
    output_content += f"# Upsun Environment Variables Migration Script\n"
    output_content += f"# Source: {args.source_env} ({args.source_project})\n"
    output_content += f"# Target: {args.target_env} ({args.target_project})\n"
    output_content += f"# Generated on: {subprocess.run('date', shell=True, capture_output=True, text=True).stdout.strip()}\n\n"
    output_content += f"# Sensitive variables:\n\n"
    output_content += '\n'.join(sensitive_commands) + '\n'
    output_content += f"\n\n# Regular variables:\n\n"
    output_content += '\n'.join(commands) + '\n'
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_content)
        print(f"Commands written to: {args.output}", file=sys.stderr)
    else:
        print(output_content)
    
    print("", file=sys.stderr)
    print(f"{colors.GREEN}Successfully generated {len(commands) + len(sensitive_commands)} variable creation commands", file=sys.stderr)
    if args.skip_inherited and skipped > 0:
        print(f"{colors.WARNING}Skipped {skipped} inherited variables", file=sys.stderr)


if __name__ == '__main__':
    main()