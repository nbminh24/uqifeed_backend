import os
import sys
import json
import yaml
from typing import Dict, List, Any

# Add parent directory to path to allow importing from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import app


def generate_openapi_spec():
    """Generate enhanced OpenAPI specification from FastAPI app"""
    print("Generating enhanced API documentation...")
    
    # Get raw OpenAPI spec from FastAPI
    raw_spec = app.openapi()
    
    # Add enhanced descriptions and examples
    enhanced_spec = enhance_openapi_spec(raw_spec)
    
    # Save as JSON
    json_path = os.path.join(os.path.dirname(__file__), "openapi_spec.json")
    with open(json_path, "w") as f:
        json.dump(enhanced_spec, f, indent=2)
    print(f"OpenAPI JSON spec saved to {json_path}")
    
    # Save as YAML
    yaml_path = os.path.join(os.path.dirname(__file__), "openapi_spec.yaml")
    with open(yaml_path, "w") as f:
        yaml.dump(enhanced_spec, f, sort_keys=False)
    print(f"OpenAPI YAML spec saved to {yaml_path}")
    
    # Generate markdown documentation
    md_path = os.path.join(os.path.dirname(__file__), "api_documentation.md")
    generate_markdown_docs(enhanced_spec, md_path)
    print(f"Markdown documentation saved to {md_path}")
    
    # Generate endpoint list by app screen
    endpoints_path = os.path.join(os.path.dirname(__file__), "endpoints_by_screen.md")
    generate_endpoints_by_screen(enhanced_spec, endpoints_path)
    print(f"Endpoints by screen saved to {endpoints_path}")


def enhance_openapi_spec(spec: Dict) -> Dict:
    """Enhance the OpenAPI spec with better descriptions and examples"""
    enhanced = spec.copy()
    
    # Add global API information
    enhanced["info"]["description"] = (
        "# UqiFeed Nutrition Tracking API\n\n"
        "This API provides backend services for the UqiFeed nutrition tracking mobile application. "
        "It includes endpoints for user authentication, food logging, nutrition analysis, "
        "statistics, notifications, and more.\n\n"
        "## Authentication\n\n"
        "Most endpoints require authentication using a JWT token. To authenticate, include the token "
        "in the Authorization header as follows: `Authorization: Bearer <token>`\n\n"
        "## Rate Limiting\n\n"
        "API requests are subject to rate limiting to prevent abuse. If you exceed the limit, "
        "you will receive a 429 Too Many Requests response."
    )
    enhanced["info"]["contact"] = {
        "name": "UqiFeed Support",
        "email": "support@uqifeed.com",
        "url": "https://uqifeed.com/support"
    }
    
    # Add enhanced path descriptions and examples
    for path, path_item in enhanced["paths"].items():
        for method, operation in path_item.items():
            if method in ["get", "post", "put", "delete", "patch"]:
                # Add example requests and responses where missing
                if "description" not in operation or not operation["description"]:
                    operation["description"] = f"This endpoint allows you to {method} the resource."
                
                # Add example responses for common status codes if missing
                if "responses" in operation:
                    for status, response in operation["responses"].items():
                        if "content" in response and "application/json" in response["content"]:
                            if "example" not in response["content"]["application/json"]:
                                # Add placeholder example based on schema (simplified)
                                schema = response["content"]["application/json"].get("schema", {})
                                response["content"]["application/json"]["example"] = generate_example_from_schema(schema)
    
    return enhanced


def generate_example_from_schema(schema: Dict) -> Any:
    """Generate a simple example value from a JSON schema definition"""
    if not schema:
        return {}
    
    schema_type = schema.get("type", "object")
    
    if "example" in schema:
        return schema["example"]
    
    if schema_type == "string":
        format_type = schema.get("format", "")
        if format_type == "date-time":
            return "2025-05-04T12:00:00Z"
        elif format_type == "date":
            return "2025-05-04"
        elif format_type == "email":
            return "user@example.com"
        else:
            return "string_value"
    
    elif schema_type == "integer":
        return 42
    
    elif schema_type == "number":
        return 42.0
    
    elif schema_type == "boolean":
        return True
    
    elif schema_type == "array":
        items = schema.get("items", {})
        return [generate_example_from_schema(items)]
    
    elif schema_type == "object":
        result = {}
        properties = schema.get("properties", {})
        for prop_name, prop_schema in properties.items():
            result[prop_name] = generate_example_from_schema(prop_schema)
        return result
    
    return {}


def generate_markdown_docs(spec: Dict, output_path: str):
    """Generate markdown documentation from OpenAPI spec"""
    with open(output_path, "w") as f:
        # Write header
        f.write(f"# {spec['info']['title']} v{spec['info']['version']}\n\n")
        f.write(f"{spec['info']['description']}\n\n")
        
        # Write table of contents
        f.write("## API Endpoints\n\n")
        
        # Group endpoints by tags
        endpoints_by_tag = {}
        for path, path_item in spec["paths"].items():
            for method, operation in path_item.items():
                if method not in ["get", "post", "put", "delete", "patch"]:
                    continue
                
                tags = operation.get("tags", ["default"])
                for tag in tags:
                    if tag not in endpoints_by_tag:
                        endpoints_by_tag[tag] = []
                    
                    endpoints_by_tag[tag].append({
                        "path": path,
                        "method": method.upper(),
                        "summary": operation.get("summary", path),
                        "operation_id": operation.get("operationId", "")
                    })
        
        # Write table of contents by tag
        for tag, endpoints in sorted(endpoints_by_tag.items()):
            f.write(f"### {tag}\n\n")
            for endpoint in endpoints:
                f.write(f"- [{endpoint['method']} {endpoint['path']}](#{endpoint['method'].lower()}-{endpoint['path'].replace('/', '-').strip('-')}): {endpoint['summary']}\n")
            f.write("\n")
        
        # Write detailed endpoint documentation
        f.write("## Detailed API Documentation\n\n")
        
        for path, path_item in spec["paths"].items():
            for method, operation in path_item.items():
                if method not in ["get", "post", "put", "delete", "patch"]:
                    continue
                
                operation_id = operation.get("operationId", f"{method}_{path}")
                summary = operation.get("summary", path)
                description = operation.get("description", "")
                
                # Write endpoint header
                f.write(f"### {method.upper()} {path}\n\n")
                f.write(f"**ID**: `{operation_id}`\n\n")
                f.write(f"**Summary**: {summary}\n\n")
                
                if description:
                    f.write(f"**Description**: {description}\n\n")
                
                # Write parameters
                parameters = operation.get("parameters", [])
                if parameters:
                    f.write("#### Parameters\n\n")
                    f.write("| Name | In | Required | Type | Description |\n")
                    f.write("|------|----|---------|----- |-------------|\n")
                    
                    for param in parameters:
                        name = param.get("name", "")
                        param_in = param.get("in", "")
                        required = "Yes" if param.get("required", False) else "No"
                        param_type = param.get("schema", {}).get("type", "")
                        description = param.get("description", "")
                        
                        f.write(f"| {name} | {param_in} | {required} | {param_type} | {description} |\n")
                    
                    f.write("\n")
                
                # Write request body if present
                if "requestBody" in operation:
                    request_body = operation["requestBody"]
                    f.write("#### Request Body\n\n")
                    
                    if "description" in request_body:
                        f.write(f"{request_body['description']}\n\n")
                    
                    if "content" in request_body:
                        for content_type, content_schema in request_body["content"].items():
                            f.write(f"Content-Type: `{content_type}`\n\n")
                            
                            if "schema" in content_schema:
                                f.write("```json\n")
                                json_schema = json.dumps(content_schema["schema"], indent=2)
                                f.write(json_schema)
                                f.write("\n```\n\n")
                            
                            if "example" in content_schema:
                                f.write("Example:\n\n")
                                f.write("```json\n")
                                example = json.dumps(content_schema["example"], indent=2)
                                f.write(example)
                                f.write("\n```\n\n")
                
                # Write responses
                if "responses" in operation:
                    f.write("#### Responses\n\n")
                    
                    for status_code, response in operation["responses"].items():
                        f.write(f"**Status Code**: {status_code}\n\n")
                        
                        if "description" in response:
                            f.write(f"**Description**: {response['description']}\n\n")
                        
                        if "content" in response:
                            for content_type, content_schema in response["content"].items():
                                f.write(f"Content-Type: `{content_type}`\n\n")
                                
                                if "example" in content_schema:
                                    f.write("Example:\n\n")
                                    f.write("```json\n")
                                    example = json.dumps(content_schema["example"], indent=2)
                                    f.write(example)
                                    f.write("\n```\n\n")
                
                f.write("---\n\n")


def generate_endpoints_by_screen(spec: Dict, output_path: str):
    """Generate a list of endpoints organized by app screen"""
    # Define mappings from API tags to app screens
    screen_mappings = {
        "users": "User Registration & Profile",
        "social-auth": "Authentication & Login",
        "dishes": "Meal Logging",
        "nutrition": "Nutrition Analysis & Statistics",
        "calories": "Home Screen & Dashboard",
        "notifications": "Settings & Notifications",
    }
    
    # Additional screen mappings for specific paths
    path_screen_mappings = {
        "/nutrition/reports/weekly-stats": "Statistics Screen",
        "/nutrition/reports/daily/{report_date}": "Dashboard",
        "/dishes/recognize": "Meal Logging - Food Recognition",
        "/dishes/daily/{date_str}": "Home Screen",
        "/users/profile": "Profile Screen",
    }
    
    # Create a structure to hold endpoints by screen
    endpoints_by_screen = {}
    
    # Process paths and operations
    for path, path_item in spec["paths"].items():
        for method, operation in path_item.items():
            if method not in ["get", "post", "put", "delete", "patch"]:
                continue
            
            # Get screen from path mapping first
            screen = None
            for path_pattern, mapped_screen in path_screen_mappings.items():
                if path_pattern in path:
                    screen = mapped_screen
                    break
            
            # If no screen from path, get from tags
            if screen is None:
                tags = operation.get("tags", [])
                for tag in tags:
                    if tag in screen_mappings:
                        screen = screen_mappings[tag]
                        break
            
            # Default screen if not found
            if screen is None:
                screen = "Other"
            
            # Add to structure
            if screen not in endpoints_by_screen:
                endpoints_by_screen[screen] = []
            
            endpoints_by_screen[screen].append({
                "path": path,
                "method": method.upper(),
                "summary": operation.get("summary", path),
                "description": operation.get("description", ""),
                "requires_auth": "security" in operation
            })
    
    # Write to markdown file
    with open(output_path, "w") as f:
        f.write("# UqiFeed API Endpoints by App Screen\n\n")
        f.write("This document organizes API endpoints by the app screens they support, to help with frontend integration.\n\n")
        
        for screen, endpoints in sorted(endpoints_by_screen.items()):
            f.write(f"## {screen}\n\n")
            
            if endpoints:
                f.write("| Method | Endpoint | Description | Auth Required |\n")
                f.write("|--------|----------|-------------|--------------|\n")
                
                for endpoint in endpoints:
                    auth = "Yes" if endpoint["requires_auth"] else "No"
                    summary = endpoint.get("summary", "").replace("|", "\\|")
                    f.write(f"| {endpoint['method']} | {endpoint['path']} | {summary} | {auth} |\n")
                
                f.write("\n")
            else:
                f.write("No endpoints mapped to this screen yet.\n\n")


if __name__ == "__main__":
    generate_openapi_spec()