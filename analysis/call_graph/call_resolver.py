# Resolve what is called
# analysis/call_graph/call_resolver.py

import builtins

def resolve_calls(calls, local_functions, imports, class_methods):
    import builtins
    builtin_funcs = set(dir(builtins))

    imported_names = set()
    for imp in imports:
        if imp["type"] == "import":
            imported_names.add(imp["module"].split(".")[0])
        elif imp["type"] == "from_import":
            imported_names.add(imp["name"])

    resolved = []

    for call in calls:
        callee = call["callee"]
        caller = call["caller"]
        class_name = call.get("class")
        obj = call.get("object")

        # 🆕 STEP-3: method resolution (ONLY self.method())
        if obj == "self" and class_name and callee in class_methods.get(class_name, set()):
            resolved.append({
                **call,
                "caller": f"{class_name}.{caller}",
                "callee": f"{class_name}.{callee}",
                "call_type": "method"
            })
            continue

        if callee in local_functions:
            call_type = "local"
            target = callee

        elif callee in imported_names:
            call_type = "imported"
            target = callee

        elif callee in builtin_funcs:
            call_type = "builtin"
            target = f"builtins.{callee}"

        else:
            call_type = "unknown"
            target = callee

        resolved.append({
            **call,
            "call_type": call_type,
            "target": target
        })
    return resolved