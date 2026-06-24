import importlib.metadata

dists = importlib.metadata.distributions()
for dist in sorted(dists, key=lambda x: x.metadata['Name'].lower()):
    print(f"{dist.metadata['Name']} ({dist.version})")
