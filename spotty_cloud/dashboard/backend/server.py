#!/usr/bin/env python

import logging
import threading
from typing import Dict, Any, Optional
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

logger = logging.getLogger(__name__)

GLOBAL_ORCHESTRATOR = None

app = Flask(__name__, static_folder="../frontend/static")
CORS(app)


@app.route("/api/status", methods=["GET"])
def get_system_status():
    """
    Get overall system status
    """
    try:
        if GLOBAL_ORCHESTRATOR:
            return jsonify(GLOBAL_ORCHESTRATOR.get_system_status())
        else:
            return jsonify(
                {"error": "Orchestrator not initialized", "status": "unavailable"}
            ), 503
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/instances", methods=["GET"])
def get_instances():
    """
    Get all active instances
    """
    try:
        if GLOBAL_ORCHESTRATOR:
            return jsonify(GLOBAL_ORCHESTRATOR.get_instance_status())
        else:
            return jsonify(
                {"error": "Orchestrator not initialized", "status": "unavailable"}
            ), 503
    except Exception as e:
        logger.error(f"Error getting instances: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/instances/<instance_id>", methods=["GET"])
def get_instance(instance_id):
    """
    Get details for a specific instance
    """
    try:
        if GLOBAL_ORCHESTRATOR:
            return jsonify(GLOBAL_ORCHESTRATOR.get_instance_status(instance_id))
        else:
            return jsonify(
                {"error": "Orchestrator not initialized", "status": "unavailable"}
            ), 503
    except Exception as e:
        logger.error(f"Error getting instance {instance_id}: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/cost/savings", methods=["GET"])
def get_cost_savings():
    """
    Get detailed cost savings information comparing spot vs on-demand pricing
    """
    try:
        if GLOBAL_ORCHESTRATOR and hasattr(GLOBAL_ORCHESTRATOR, "cost_tracker"):
            days = request.args.get("days", default=7, type=int)
            historical_data = GLOBAL_ORCHESTRATOR.cost_tracker.get_historical_data(days)
            summary = GLOBAL_ORCHESTRATOR.cost_tracker.get_summary()

            return jsonify(
                {
                    "summary": summary,
                    "historical": historical_data,
                    "projected_monthly_savings": round(
                        summary.get("total_savings", 0) * 30, 2
                    )
                    if summary
                    else 0,
                }
            )
        else:
            return jsonify(
                {"error": "Cost tracker not initialized", "status": "unavailable"}
            ), 503
    except Exception as e:
        logger.error(f"Error getting cost savings: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/instances/<instance_id>/terminate", methods=["POST"])
def terminate_instance(instance_id):
    """
    Terminate a specific instance for resilience testing
    """
    try:
        if GLOBAL_ORCHESTRATOR:
            success = GLOBAL_ORCHESTRATOR.trigger_instance_failure(instance_id)
            return jsonify({"success": success})
        else:
            return jsonify(
                {"error": "Orchestrator not initialized", "status": "unavailable"}
            ), 503
    except Exception as e:
        logger.error(
            f"Error terminating instance {instance_id}: {str(e)}", exc_info=True
        )
        return jsonify({"error": str(e)}), 500


@app.route("/api/workloads", methods=["GET"])
def get_workloads():
    """
    Get all workloads
    """
    try:
        if GLOBAL_ORCHESTRATOR and hasattr(GLOBAL_ORCHESTRATOR, "workload_dispatcher"):
            workloads = GLOBAL_ORCHESTRATOR.workload_dispatcher.workloads
            result = {}
            for workload_id, details in workloads.items():
                result[workload_id] = GLOBAL_ORCHESTRATOR.get_workload_status(
                    workload_id
                )
            return jsonify(result)
        else:
            return jsonify(
                {
                    "error": "Workload dispatcher not initialized",
                    "status": "unavailable",
                }
            ), 503
    except Exception as e:
        logger.error(f"Error getting workloads: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/workloads/<workload_id>", methods=["GET"])
def get_workload(workload_id):
    """
    Get details for a specific workload
    """
    try:
        if GLOBAL_ORCHESTRATOR:
            return jsonify(GLOBAL_ORCHESTRATOR.get_workload_status(workload_id))
        else:
            return jsonify(
                {"error": "Orchestrator not initialized", "status": "unavailable"}
            ), 503
    except Exception as e:
        logger.error(f"Error getting workload {workload_id}: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/workloads", methods=["POST"])
def submit_workload():
    """
    Submit a new workload
    """
    try:
        if not GLOBAL_ORCHESTRATOR:
            return jsonify(
                {"error": "Orchestrator not initialized", "status": "unavailable"}
            ), 503

        workload_config = request.json
        if not workload_config:
            return jsonify({"error": "Missing workload configuration"}), 400

        workload_id = GLOBAL_ORCHESTRATOR.submit_workload(workload_config)
        return jsonify({"workload_id": workload_id, "status": "submitted"})
    except Exception as e:
        logger.error(f"Error submitting workload: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/costs", methods=["GET"])
def get_costs():
    """
    Get cost data
    """
    try:
        if GLOBAL_ORCHESTRATOR and hasattr(GLOBAL_ORCHESTRATOR, "cost_tracker"):
            return jsonify(GLOBAL_ORCHESTRATOR.cost_tracker.get_current_cost_data())
        else:
            return jsonify(
                {"error": "Cost tracker not initialized", "status": "unavailable"}
            ), 503
    except Exception as e:
        logger.error(f"Error getting costs: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/costs/history", methods=["GET"])
def get_cost_history():
    """
    Get historical cost data
    """
    try:
        days = int(request.args.get("days", 7))
        if GLOBAL_ORCHESTRATOR and hasattr(GLOBAL_ORCHESTRATOR, "cost_tracker"):
            return jsonify(GLOBAL_ORCHESTRATOR.cost_tracker.get_historical_data(days))
        else:
            return jsonify(
                {"error": "Cost tracker not initialized", "status": "unavailable"}
            ), 503
    except Exception as e:
        logger.error(f"Error getting cost history: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/templates", methods=["GET"])
def get_workload_templates():
    """
    Get available workload templates
    """
    try:
        templates = {
            "cpu_workload": {
                "name": "CPU Workload",
                "description": "Standard compute-intensive workload",
                "type": "cpu",
                "resources": {"cpu": 2, "memory": 2, "gpu": 0},
                "timeout": 3600,
            },
            "gpu_workload": {
                "name": "GPU Workload",
                "description": "Graphics-intensive processing task",
                "type": "gpu",
                "resources": {"cpu": 2, "memory": 4, "gpu": 1},
                "timeout": 7200,
            },
            "edge_workload": {
                "name": "Edge Computing Simulation",
                "description": "Simulates edge device computation",
                "type": "edge",
                "resources": {"cpu": 1, "memory": 1, "gpu": 0},
                "timeout": 1800,
            },
            "video_encoding": {
                "name": "Video Encoding",
                "description": "Convert videos to multiple formats",
                "type": "video",
                "resources": {"cpu": 2, "memory": 2, "gpu": 1},
                "timeout": 3600,
            },
        }
        return jsonify(templates)
    except Exception as e:
        logger.error(f"Error getting workload templates: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    """
    Serve the frontend dashboard
    """
    if not path or path == "index.html":
        return send_from_directory("../frontend", "index.html")
    return send_from_directory("../frontend", path)


def start_dashboard_server(
    port: int = 8080,
    host: str = "0.0.0.0",
    debug: bool = False,
    config: Optional[Dict[str, Any]] = None,
    orchestrator=None,
) -> threading.Thread:
    """
    Start the dashboard server in a separate thread

    Args:
        port: Port to listen on
        host: Host to bind to
        debug: Enable Flask debug mode
        config: Configuration dictionary
        orchestrator: Reference to the orchestrator

    Returns:
        thread: Server thread
    """
    global GLOBAL_ORCHESTRATOR
    GLOBAL_ORCHESTRATOR = orchestrator

    logger.info(f"Starting dashboard server on {host}:{port}")

    def run_server():
        try:
            app.run(host=host, port=port, debug=debug, use_reloader=False)
        except Exception as e:
            logger.error(f"Error running dashboard server: {str(e)}", exc_info=True)

    thread = threading.Thread(target=run_server)
    thread.daemon = True
    thread.start()

    logger.info("Dashboard server started in background thread")
    return thread
