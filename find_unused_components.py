
import yaml


def get_security_references(obj, refs=None):
    """Get security scheme references from security fields."""
    if refs is None:
        refs = set()

    if isinstance(obj, dict):
        # Check if this is a security requirement object
        if "security" in obj:
            for security_req in obj["security"]:
                for scheme_name in security_req.keys():
                    refs.add(f"securitySchemes/{scheme_name}")
        # Recursively check other fields
        for value in obj.values():
            get_security_references(value, refs)
    elif isinstance(obj, list):
        for item in obj:
            get_security_references(item, refs)

    return refs


def get_referenced_components(obj, refs=None):
    """Recursively find all component references in an object."""
    if refs is None:
        refs = set()

    if isinstance(obj, dict):
        for key, value in obj.items():
            # Check for $ref keys that point to components
            if (
                key == "$ref"
                and isinstance(value, str)
                and value.startswith("#/components/")
            ):
                refs.add(value.replace("#/components/", ""))
            else:
                get_referenced_components(value, refs)
    elif isinstance(obj, list):
        for item in obj:
            get_referenced_components(item, refs)

    return refs


def should_exclude_path(path):
    """Check if path should be excluded based on prefixes."""
    exclude_prefixes = [
        "/api/environments/{project_id}/batch_exports/",
        "/api/environments/{project_id}/exports/",
        "/api/environments/{project_id}/subscriptions/",
        "/api/organizations/",
        "/api/environments/{project_id}/web_vitals/",
        "/api/projects/{project_id}/batch_exports/",
        "/api/projects/{project_id}/dashboard_templates/",
        "/api/projects/{project_id}/file_system/",
        "/api/projects/{project_id}/notebooks/",
        "/api/projects/{project_id}/plugin_configs/",
    ]
    return any(path.startswith(prefix) for prefix in exclude_prefixes)


def clean_method_object(method_obj):
    """Remove tags and security sections from method object."""
    if isinstance(method_obj, dict):
        method_obj.pop("tags", None)
        method_obj.pop("security", None)
    return method_obj


def get_components_for_get_methods(schema):
    """Get components used only in GET methods."""
    get_refs = set()
    get_security_refs = set()
    get_paths = {}

    # Filter for GET methods and collect their references
    for path, path_item in schema["paths"].items():
        if "get" in path_item and not should_exclude_path(path):
            # Clean the GET method object before adding
            get_method = clean_method_object(path_item["get"])
            get_paths[path] = {"get": get_method}
            get_referenced_components(path_item["get"], get_refs)
            get_security_references(path_item["get"], get_security_refs)

    # Keep recursively finding references until no new ones are found
    prev_size = 0
    while len(get_refs) != prev_size:
        prev_size = len(get_refs)
        # Check for nested references in already found components
        for ref in list(get_refs):
            category, name = ref.split("/")
            if (
                category in schema["components"]
                and name in schema["components"][category]
            ):
                component = schema["components"][category][name]
                get_referenced_components(component, get_refs)
                get_security_references(component, get_security_refs)

    # Create new components dict with only used components
    new_components = {}
    for ref in get_refs:
        category, name = ref.split("/")
        if category not in new_components:
            new_components[category] = {}
        new_components[category][name] = schema["components"][category][name]

    # Add used security schemes
    if get_security_refs:
        new_components["securitySchemes"] = {}
        for ref in get_security_refs:
            _, name = ref.split("/")
            new_components["securitySchemes"][name] = schema["components"][
                "securitySchemes"
            ][name]

    # Remove timezone enum and its references
    if "schemas" in new_components:
        # Remove direct timezone enum
        if "TimezoneEnum" in new_components["schemas"]:
            del new_components["schemas"]["TimezoneEnum"]

        # Remove timezone references from other schemas
        for schema_name, schema_def in new_components["schemas"].items():
            if isinstance(schema_def, dict):
                if "properties" in schema_def:
                    for prop_name, prop_def in schema_def["properties"].items():
                        if isinstance(prop_def, dict):
                            # Remove timezone references
                            if (
                                prop_def.get("$ref")
                                == "#/components/schemas/TimezoneEnum"
                            ):
                                schema_def["properties"][prop_name] = {"type": "string"}
                            elif "oneOf" in prop_def:
                                prop_def["oneOf"] = [
                                    ref
                                    for ref in prop_def["oneOf"]
                                    if not (
                                        isinstance(ref, dict)
                                        and ref.get("$ref")
                                        == "#/components/schemas/TimezoneEnum"
                                    )
                                ]

    return get_paths, new_components


def create_get_only_schema(input_path, output_path):
    """Create a new OpenAPI schema with only GET methods and their components."""
    # First count the lines
    with open(input_path, "r") as f:
        original_lines = sum(1 for _ in f)

    # Then load the schema
    with open(input_path, "r") as f:
        schema = yaml.safe_load(f)

    original_path_count = len(schema["paths"])
    get_paths, used_components = get_components_for_get_methods(schema)

    new_schema = {
        "openapi": schema["openapi"],
        "info": schema["info"],
        "paths": get_paths,
        "components": used_components,
    }

    # Preserve any top-level fields that aren't paths, components, or x-tagGroups
    for key, value in schema.items():
        if key not in ["paths", "components", "x-tagGroups"]:
            new_schema[key] = value

    with open(output_path, "w") as f:
        yaml.dump(new_schema, f, sort_keys=False)

    with open(output_path, "r") as f:
        new_lines = sum(1 for _ in f)

    return len(get_paths), original_path_count, original_lines, new_lines


if __name__ == "__main__":
    input_path = "/Users/parthgandhi/Downloads/schema.yaml"
    output_path = "/Users/parthgandhi/Downloads/schema_get_only.yaml"
    remaining_paths, original_paths, original_lines, new_lines = create_get_only_schema(
        input_path, output_path
    )
    removed_paths = original_paths - remaining_paths

    print("Created new schema with only GET methods at:", output_path)
    print(f"Original number of endpoints: {original_paths}")
    print(f"Number of remaining endpoints: {remaining_paths}")
    print(f"Number of removed endpoints: {removed_paths}")
    print(f"Original file lines: {original_lines}")
    print(f"New file lines: {new_lines}")
    print(f"Lines removed: {original_lines - new_lines}")
