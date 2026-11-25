"""Campus Pulse - a tiny study-task tracker API.

This is the application that our CI/CD pipeline builds, tests, containerises
and deploys to Kubernetes. It is deliberately small: the assignment grades
the AUTOMATION around the app, not the app's complexity.

Key ideas demonstrated here (each one maps to a pipeline/Kubernetes concept):
  * /health   -> used by Docker HEALTHCHECK and Kubernetes readiness/liveness probes
  * /version  -> proves WHICH release is running after a rolling update
  * GREETING / APP_ENV   -> non-sensitive config, injected from a Kubernetes ConfigMap
  * API_KEY              -> sensitive config, injected from a Kubernetes Secret
"""
import os

from flask import Flask, jsonify, request


def create_app(api_key=None):
    """Application factory.

    Using a factory (instead of one global app) lets every unit test create a
    brand-new app with its own empty task list, so tests never affect each other.

    Args:
        api_key: Optional override used by tests. If None, the key is read from
                 the API_KEY environment variable (set from a Kubernetes Secret).
    """
    app = Flask(__name__)

    # If key is an empty string, authentication is switched off (handy locally).
    key = api_key if api_key is not None else os.getenv("API_KEY", "")

    # In-memory storage: simple on purpose. Restarting a pod empties it.
    # (A real system would use a database, which is out of scope here.)
    tasks = {}                 # task_id -> task dictionary
    counter = {"next": 1}      # dict so inner functions can modify it (closure)

    # ------------------------------------------------------------------ security
    @app.before_request
    def require_key_for_writes():
        """Runs before EVERY request. Protects write operations only.

        GET requests (including /health used by probes) stay public, so
        Kubernetes can always check health without needing the secret.
        """
        if key and request.method in ("POST", "PUT", "DELETE"):
            if request.headers.get("X-API-Key") != key:
                return jsonify(error="invalid or missing API key"), 401

    # ------------------------------------------------------- operational endpoints
    @app.get("/")
    def index():
        """Landing page. GREETING and APP_ENV prove the ConfigMap is wired in."""
        return jsonify(
            name="Campus Pulse",
            message=os.getenv("GREETING", "Hello from Campus Pulse"),
            environment=os.getenv("APP_ENV", "local"),
        )

    @app.get("/health")
    def health():
        """Liveness/readiness target. Must be fast and need no dependencies."""
        return jsonify(status="ok")

    @app.get("/version")
    def version():
        """Reports the release baked into the image at build time.

        The Dockerfile sets APP_VERSION and GIT_SHA from build arguments, so
        after a deployment we can curl this endpoint and confirm the new
        version is really the one serving traffic.
        """
        return jsonify(
            version=os.getenv("APP_VERSION", "dev"),
            commit=os.getenv("GIT_SHA", "unknown"),
        )

    # ------------------------------------------------------------ business endpoints
    @app.get("/tasks")
    def list_tasks():
        """List all tasks. Optional filter: /tasks?course=Infra"""
        course = request.args.get("course")
        items = [t for t in tasks.values() if not course or t["course"] == course]
        return jsonify(items)

    @app.post("/tasks")
    def create_task():
        """Create a task. JSON body: {"title": "...", "course": "..."}"""
        # silent=True -> bad/missing JSON gives None instead of raising an error
        data = request.get_json(silent=True) or {}
        title = data.get("title")

        # Input validation: title must be a non-empty string
        if not isinstance(title, str) or not title.strip():
            return jsonify(error="title is required"), 400

        task = {
            "id": counter["next"],
            "title": title.strip(),
            "course": data.get("course", "general"),
            "done": False,
        }
        tasks[task["id"]] = task
        counter["next"] += 1
        return jsonify(task), 201        # 201 = Created

    @app.get("/tasks/<int:task_id>")
    def get_task(task_id):
        """Fetch a single task by id (404 if it does not exist)."""
        task = tasks.get(task_id)
        if task is None:
            return jsonify(error="task not found"), 404
        return jsonify(task)

    @app.put("/tasks/<int:task_id>/done")
    def complete_task(task_id):
        """Mark a task as completed."""
        task = tasks.get(task_id)
        if task is None:
            return jsonify(error="task not found"), 404
        task["done"] = True
        return jsonify(task)

    @app.delete("/tasks/<int:task_id>")
    def delete_task(task_id):
        """Delete a task. Returns 204 (No Content) on success."""
        if tasks.pop(task_id, None) is None:
            return jsonify(error="task not found"), 404
        return "", 204

    return app


# Module-level instance. gunicorn (our production server inside the container)
# starts the app with:  gunicorn app.main:app   (module "app.main", variable "app")
app = create_app()
