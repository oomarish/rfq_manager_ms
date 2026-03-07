import json

with open("newman_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

executions = data.get("run", {}).get("executions", [])

with open("test_trace.txt", "w", encoding="utf-8") as out:
    for ex in executions:
        item_name = ex.get("item", {}).get("name", "Unknown Request")
        
        # get response status code
        res = ex.get("response", {})
        status = res.get("code", "NO-RESPONSE")
        
        out.write(f"[{status}] {item_name}\n")
        
        assertions = ex.get("assertions", [])
        for a in assertions:
            if "error" in a and a["error"]:
                out.write(f"   -> FAIL: {a['error']['message']}\n")
