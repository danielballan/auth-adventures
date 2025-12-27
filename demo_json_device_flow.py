#!/usr/bin/env python3
"""
Demo script showing how to use the updated device code flow with JSON support.
"""

# This demo shows how the updated client can be used
# Requires httpx package to run actual demo

def demo_json_usage():
    """
    Example of how to use the device code flow with JSON.
    """
    print("Device Code Flow JSON Support Demo")
    print("===================================")
    
    print("\nBefore the update:")
    print("- Only form data was supported")
    print("- Client sent: data={'device_code': 'xyz'}")
    print("- Server expected form data only")
    
    print("\nAfter the update:")
    print("- Both JSON and form data are supported")
    print("- Client can send JSON: json={'device_code': 'xyz'}")
    print("- Client can still send form data: data={'device_code': 'xyz'}")
    print("- Server auto-detects content type and handles both")
    
    print("\nExample usage:")
    print("")
    print("# Using JSON (new default)")
    print("from client_device_code_flow import login")
    print("import httpx")
    print("")
    print("client = httpx.Client(base_url='http://localhost:8000')")
    print("login(client, use_json=True)  # Send JSON requests")
    print("")
    print("# Using form data (backward compatible)")
    print("login(client, use_json=False)  # Send form data")
    print("")
    
    print("\nAPI Endpoints now support:")
    print("- POST /token - accepts JSON or form data")
    print("- POST /refresh - accepts JSON or form data")
    print("- Content-Type: application/json -> JSON parsing")
    print("- Other/missing Content-Type -> form data parsing")
    
    print("\nRefresh Flow also updated:")
    print("RefreshFlow(tokens, refresh_url, use_json=True)  # JSON")
    print("RefreshFlow(tokens, refresh_url, use_json=False) # Form data")

def show_server_changes():
    """
    Show the key server-side changes made.
    """
    print("\n\nServer-side Changes")
    print("==================")
    
    print("\nAdded get_request_data() function:")
    print("")
    print("async def get_request_data(request):")
    print('    content_type = request.headers.get("content-type", "")')
    print('    if content_type.startswith("application/json"):')
    print("        return await request.json()")
    print("    else:")
    print("        form_data = await request.form()")
    print("        return dict(form_data)")
    
    print("\nUpdated endpoints to use this function:")
    print("- /token endpoint")
    print("- /refresh endpoint")
    print("- /device_code_form endpoint")
    
    print("\nBackward compatibility maintained:")
    print("- Existing clients using form data continue to work")
    print("- New clients can use JSON for cleaner integration")

if __name__ == "__main__":
    demo_json_usage()
    show_server_changes()
    
    print("\n\n✓ Device code flow now supports JSON!")
    print("  Ready for modern API integration.")
