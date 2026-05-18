#!/usr/bin/env python3
"""
Seed the database with a demo project and tasks.
Usage: python3 scripts/seed.py [repo_path]
"""
import sys
import json
import urllib.request
import urllib.error

API = "http://localhost:8000"

def post(path: str, data: dict) -> dict:
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{API}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main():
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/demo-repo"

    print(f"Seeding with repo_path={repo_path}")

    project = post("/api/v1/projects", {
        "name": "Demo Project",
        "description": "A demo project to test the AI Agent Control Plane",
        "repo_path": repo_path,
        "default_branch": "main",
    })
    print(f"Created project: {project['id']} — {project['name']}")

    tasks = [
        {"title": "Add a README to the project", "description": "Create a README.md with project overview and setup instructions."},
        {"title": "Write a hello world script", "description": "Create a hello.py that prints 'Hello from the AI Agent Control Plane!'"},
        {"title": "Add .gitignore", "description": "Add a .gitignore appropriate for a Python project."},
    ]

    for task_data in tasks:
        task = post(f"/api/v1/projects/{project['id']}/tasks", task_data)
        print(f"  Created task: {task['id']} — {task['title']}")

    print(f"\nOpen http://localhost:3000/projects/{project['id']} to view the board.")


if __name__ == "__main__":
    main()
