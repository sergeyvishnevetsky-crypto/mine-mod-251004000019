from wsgi import app

print("{:<35} {:<12} {}".format("RULE", "METHODS", "ENDPOINT"))
print("-"*72)
with app.app_context():
    rules = sorted(app.url_map.iter_rules(), key=lambda r: r.rule)
    for r in rules:
        methods = ",".join(sorted(m for m in r.methods if m not in ("HEAD","OPTIONS")))
        print("{:<35} {:<12} {}".format(r.rule, methods, r.endpoint))
