#!/usr/bin/env python
# GUI for video encoding orchestration using Streamlit

import streamlit as st
import os
import subprocess
import time
import pandas as pd
import numpy as np
import json
import glob
import threading
import queue
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
from encode_videos import (
    RESOLUTION_PRESETS,
    SAMPLE_VIDEOS,
    download_sample_video,
    download_file,
)

# Set page configuration
st.set_page_config(
    page_title="Video Encoding Dashboard",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state for job tracking
if "jobs" not in st.session_state:
    st.session_state.jobs = []
if "job_count" not in st.session_state:
    st.session_state.job_count = 0
if "logs" not in st.session_state:
    st.session_state.logs = []
if "resource_history" not in st.session_state:
    st.session_state.resource_history = {
        "timestamps": [],
        "cpu": [],
        "memory": [],
        "gpu": [],
    }


# Function to get current resource usage
def get_resource_usage():
    try:
        # CPU usage (simplified)
        cpu_usage = (
            np.random.randint(10, 90)
            if st.session_state.active_jobs > 0
            else np.random.randint(0, 20)
        )

        # Memory usage (simplified)
        memory_usage = (
            np.random.randint(20, 80)
            if st.session_state.active_jobs > 0
            else np.random.randint(10, 30)
        )

        # GPU usage (if available, simplified)
        gpu_usage = (
            np.random.randint(30, 100)
            if st.session_state.active_jobs > 0 and st.session_state.use_gpu
            else 0
        )

        return {
            "timestamp": datetime.now(),
            "cpu": cpu_usage,
            "memory": memory_usage,
            "gpu": gpu_usage,
        }
    except Exception as e:
        st.error(f"Error getting resource usage: {str(e)}")
        return {"timestamp": datetime.now(), "cpu": 0, "memory": 0, "gpu": 0}


# Background thread for encoding
def encoding_worker(
    job_id, input_path, output_dir, formats, use_gpu, crf, result_queue
):
    try:
        # Simulate encoding process with progress updates
        formats_list = formats.split(",")
        total_formats = len(formats_list)

        for i, fmt in enumerate(formats_list):
            # Update progress
            progress = {
                "job_id": job_id,
                "status": "running",
                "progress": (i / total_formats) * 100,
            }
            result_queue.put(progress)

            # Simulate encoding time based on format resolution and GPU usage
            if fmt == "1080p":
                sleep_time = 10 if use_gpu else 25
            elif fmt == "720p":
                sleep_time = 7 if use_gpu else 18
            elif fmt == "480p":
                sleep_time = 5 if use_gpu else 12
            else:
                sleep_time = 3 if use_gpu else 8

            # Add some randomness
            sleep_time = sleep_time * (0.8 + 0.4 * np.random.random())

            # Simulate encoding by sleeping
            time.sleep(sleep_time / 10)  # Reduced time for demo purposes

            # Log format completion
            log_msg = f"Job {job_id}: Completed encoding {os.path.basename(input_path)} to {fmt}"
            result_queue.put({"type": "log", "message": log_msg})

        # Final update
        result_queue.put({"job_id": job_id, "status": "completed", "progress": 100})
        result_queue.put(
            {
                "type": "log",
                "message": f"Job {job_id}: All formats completed for {os.path.basename(input_path)}",
            }
        )
    except Exception as e:
        result_queue.put({"job_id": job_id, "status": "failed", "error": str(e)})
        result_queue.put({"type": "log", "message": f"Job {job_id}: Failed - {str(e)}"})


# Function to create a new encoding job
def create_encoding_job(input_path, output_dir, formats, use_gpu, crf):
    job_id = st.session_state.job_count
    st.session_state.job_count += 1

    new_job = {
        "id": job_id,
        "input": input_path,
        "output": output_dir,
        "formats": formats,
        "use_gpu": use_gpu,
        "crf": crf,
        "status": "pending",
        "progress": 0,
        "start_time": datetime.now(),
        "end_time": None,
    }

    st.session_state.jobs.append(new_job)
    st.session_state.logs.append(
        f"Job {job_id}: Created new encoding job for {os.path.basename(input_path)}"
    )

    # Start the encoding in a background thread
    result_queue = queue.Queue()
    thread = threading.Thread(
        target=encoding_worker,
        args=(job_id, input_path, output_dir, formats, use_gpu, crf, result_queue),
    )
    thread.daemon = True
    thread.start()

    return job_id, result_queue


# Function to process updates from encoding threads
def process_job_updates():
    if "job_queues" in st.session_state and st.session_state.job_queues:
        st.session_state.active_jobs = 0

        for job_id, q in list(st.session_state.job_queues.items()):
            try:
                while not q.empty():
                    update = q.get(block=False)

                    if "type" in update and update["type"] == "log":
                        # This is a log message
                        st.session_state.logs.append(update["message"])
                    else:
                        # This is a job status update
                        job_id = update["job_id"]

                        # Find and update the job
                        for job in st.session_state.jobs:
                            if job["id"] == job_id:
                                job["status"] = update["status"]
                                if "progress" in update:
                                    job["progress"] = update["progress"]
                                if (
                                    update["status"] == "completed"
                                    or update["status"] == "failed"
                                ):
                                    job["end_time"] = datetime.now()
                                break
            except Exception as e:
                st.error(f"Error processing job updates: {str(e)}")

        # Count active jobs
        st.session_state.active_jobs = sum(
            1 for job in st.session_state.jobs if job["status"] == "running"
        )


# Update resource history
def update_resource_history():
    # Get current usage
    usage = get_resource_usage()

    # Add to history
    st.session_state.resource_history["timestamps"].append(usage["timestamp"])
    st.session_state.resource_history["cpu"].append(usage["cpu"])
    st.session_state.resource_history["memory"].append(usage["memory"])
    st.session_state.resource_history["gpu"].append(usage["gpu"])

    # Keep only the last 30 data points
    max_history = 30
    if len(st.session_state.resource_history["timestamps"]) > max_history:
        st.session_state.resource_history["timestamps"] = (
            st.session_state.resource_history["timestamps"][-max_history:]
        )
        st.session_state.resource_history["cpu"] = st.session_state.resource_history[
            "cpu"
        ][-max_history:]
        st.session_state.resource_history["memory"] = st.session_state.resource_history[
            "memory"
        ][-max_history:]
        st.session_state.resource_history["gpu"] = st.session_state.resource_history[
            "gpu"
        ][-max_history:]


# Initialize active jobs counter
if "active_jobs" not in st.session_state:
    st.session_state.active_jobs = 0

# Initialize job queues dictionary
if "job_queues" not in st.session_state:
    st.session_state.job_queues = {}

# Set base paths (adjust for your environment)
input_base_dir = "./input"
output_base_dir = "./output"

# Initialize use_gpu flag
if "use_gpu" not in st.session_state:
    st.session_state.use_gpu = False

# Main app structure
st.title("🎬 Video Encoding Orchestration Dashboard")

# Sidebar for configuration
with st.sidebar:
    st.header("Configure Encoding")

    # GPU/CPU selector
    st.session_state.use_gpu = st.checkbox(
        "Use GPU for encoding", value=st.session_state.use_gpu
    )

    st.subheader("Video Source")
    source_type = st.radio(
        "Select video source", options=["Sample Videos", "URL", "Local Files"], index=0
    )

    # Different input options based on selection
    if source_type == "Sample Videos":
        sample_options = list(SAMPLE_VIDEOS.keys())
        selected_sample = st.selectbox("Select a sample video", sample_options)

        # Show sample details
        if selected_sample:
            sample = SAMPLE_VIDEOS[selected_sample]
            st.info(f"{sample['description']}\nSize: ~{sample['size_mb']} MB")

    elif source_type == "URL":
        video_url = st.text_input("Enter video URL")

    elif source_type == "Local Files":
        st.info("Using files already in the input directory")
        local_files = ["[Refresh to see files]"]
        try:
            # Get list of video files in input directory
            extensions = [".mp4", ".avi", ".mov", ".mkv"]
            local_files = []
            for ext in extensions:
                local_files.extend(glob.glob(os.path.join(input_base_dir, f"*{ext}")))
                local_files.extend(
                    glob.glob(os.path.join(input_base_dir, f"**/*{ext}"))
                )

            local_files = [os.path.basename(f) for f in local_files] or [
                "No video files found"
            ]
        except Exception as e:
            st.error(f"Error listing files: {str(e)}")

        selected_file = st.selectbox("Select local file", local_files)

    st.subheader("Encoding Parameters")

    # Resolution formats
    available_formats = list(RESOLUTION_PRESETS.keys())
    selected_formats = st.multiselect(
        "Select output formats", available_formats, default=["720p", "480p"]
    )

    # Quality setting
    crf_value = st.slider("Quality (CRF, lower is better)", 0, 51, 23)

    # Action buttons
    if st.button("Start Encoding"):
        if not selected_formats:
            st.error("Please select at least one output format")
        else:
            input_path = ""
            formats_str = ",".join(selected_formats)

            # Handle different source types
            if source_type == "Sample Videos":
                # Download the sample if needed
                st.session_state.logs.append(
                    f"Downloading sample video: {selected_sample}"
                )
                input_path = (
                    download_sample_video(selected_sample, input_base_dir) or ""
                )

            elif source_type == "URL" and video_url:
                # Download from URL
                filename = video_url.split("/")[-1]
                output_path = os.path.join(input_base_dir, filename)
                st.session_state.logs.append(f"Downloading video from URL: {video_url}")

                if download_file(video_url, output_path):
                    input_path = output_path
                else:
                    st.error("Failed to download video from URL")

            elif (
                source_type == "Local Files"
                and selected_file
                and selected_file != "No video files found"
            ):
                # Use selected local file
                input_path = os.path.join(input_base_dir, selected_file)

            # Create and start the encoding job
            if input_path:
                job_id, queue = create_encoding_job(
                    input_path,
                    output_base_dir,
                    formats_str,
                    st.session_state.use_gpu,
                    crf_value,
                )
                st.session_state.job_queues[job_id] = queue
                st.success(f"Started encoding job (ID: {job_id})")
            else:
                st.error("No valid input video selected or downloaded")

# Main content area with tabs
tab1, tab2, tab3, tab4 = st.tabs(
    ["Active Jobs", "Job History", "Resource Monitor", "Logs"]
)

# Process job updates
process_job_updates()

# Update resource history
update_resource_history()

# Tab 1: Active Jobs
with tab1:
    st.subheader("Active Encoding Jobs")

    if not st.session_state.jobs or all(
        job["status"] in ["completed", "failed"] for job in st.session_state.jobs
    ):
        st.info("No active encoding jobs. Use the sidebar to start a new job.")
    else:
        active_jobs = [
            job
            for job in st.session_state.jobs
            if job["status"] not in ["completed", "failed"]
        ]

        for job in active_jobs:
            col1, col2 = st.columns([3, 1])

            with col1:
                st.progress(job["progress"] / 100)

            with col2:
                st.write(
                    f"Job {job['id']}: {job['status'].capitalize()} - {job['progress']:.1f}%"
                )

            st.write(f"Input: {os.path.basename(job['input'])}")
            st.write(f"Formats: {job['formats']}")
            st.write(f"GPU: {'Yes' if job['use_gpu'] else 'No'}")
            st.write(f"Started: {job['start_time'].strftime('%H:%M:%S')}")
            st.write("---")

# Tab 2: Job History
with tab2:
    st.subheader("Job History")

    if not st.session_state.jobs:
        st.info("No encoding jobs yet.")
    else:
        # Create a DataFrame for the job history
        job_data = []
        for job in st.session_state.jobs:
            duration = "-"
            if job["end_time"] and job["start_time"]:
                duration = (job["end_time"] - job["start_time"]).total_seconds()
                duration = f"{duration:.1f}s"

            job_data.append(
                {
                    "ID": job["id"],
                    "Input": os.path.basename(job["input"]),
                    "Formats": job["formats"],
                    "GPU": "Yes" if job["use_gpu"] else "No",
                    "Status": job["status"].capitalize(),
                    "Progress": f"{job['progress']:.1f}%",
                    "Duration": duration,
                    "Started": job["start_time"].strftime("%H:%M:%S"),
                }
            )

        job_df = pd.DataFrame(job_data)
        st.dataframe(job_df, use_container_width=True)

# Tab 3: Resource Monitor
with tab3:
    st.subheader("System Resource Utilization")

    # Create three columns
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Active Jobs", st.session_state.active_jobs)

    # Get latest resource usage
    if st.session_state.resource_history["timestamps"]:
        latest_cpu = st.session_state.resource_history["cpu"][-1]
        latest_memory = st.session_state.resource_history["memory"][-1]
        latest_gpu = st.session_state.resource_history["gpu"][-1]

        with col2:
            st.metric("CPU Usage", f"{latest_cpu}%")
        with col3:
            st.metric("Memory Usage", f"{latest_memory}%")

    # Only show GPU if it's being used
    if st.session_state.use_gpu and st.session_state.resource_history["timestamps"]:
        st.metric("GPU Usage", f"{latest_gpu}%")

    # Resource usage over time chart
    if len(st.session_state.resource_history["timestamps"]) > 1:
        st.subheader("Resource Usage Over Time")

        # Create figure and axis
        fig, ax = plt.subplots(figsize=(10, 5))

        # Convert timestamps to strings for display
        timestamps = [
            ts.strftime("%H:%M:%S")
            for ts in st.session_state.resource_history["timestamps"]
        ]

        # Plot CPU and memory
        ax.plot(
            timestamps,
            st.session_state.resource_history["cpu"],
            label="CPU %",
            marker="o",
            linestyle="-",
            alpha=0.7,
        )
        ax.plot(
            timestamps,
            st.session_state.resource_history["memory"],
            label="Memory %",
            marker="s",
            linestyle="-",
            alpha=0.7,
        )

        # Plot GPU if used
        if st.session_state.use_gpu:
            ax.plot(
                timestamps,
                st.session_state.resource_history["gpu"],
                label="GPU %",
                marker="^",
                linestyle="-",
                alpha=0.7,
            )

        # Set labels and legend
        ax.set_xlabel("Time")
        ax.set_ylabel("Utilization %")
        ax.set_ylim(0, 100)
        ax.legend()

        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Show plot
        st.pyplot(fig)

# Tab 4: Logs
with tab4:
    st.subheader("System Logs")

    # Options for logs
    auto_scroll = st.checkbox("Auto-scroll to bottom", value=True)
    clear_logs = st.button("Clear Logs")

    if clear_logs:
        st.session_state.logs = []

    # Display logs
    log_container = st.container()

    with log_container:
        for log in st.session_state.logs:
            st.text(log)

    # Auto-scroll to bottom if enabled
    if auto_scroll and st.session_state.logs:
        js = f"""
        <script>
            function scroll_to_bottom() {{{{                
                var logs = document.querySelector('.stContainer');
                if (logs) logs.scrollTop = logs.scrollHeight;
            }}}}
            scroll_to_bottom();
        </script>
        """
        st.components.v1.html(js)

# Orchestration visualization
st.subheader("Orchestration Workflow")

# Visualize the workflow
workflow_graph = """
 digraph G {
    rankdir=LR;
    node [shape=box, style=filled, fontname=Arial];
    
    input [label="Input Videos", fillcolor="#AED6F1"];
    encoder [label="Video Encoder\n(CPU/GPU)", fillcolor="#F5B041"];
    storage [label="Storage", fillcolor="#A9DFBF"];
    output [label="Output Formats", fillcolor="#D7BDE2"];
    
    input -> encoder;
    encoder -> storage;
    storage -> output;
    
    {rank=same; input; storage;}
    {rank=same; encoder; output;}
}
"""

# Display using Graphviz if installed
try:
    from graphviz import Source

    graph = Source(workflow_graph)
    st.graphviz_chart(workflow_graph)
except ImportError:
    st.write(
        "Workflow visualization requires graphviz. Install with: pip install graphviz"
    )
    st.code(workflow_graph, language="dot")


# Add Streamlit to requirements file if not already there
def ensure_streamlit_in_requirements():
    req_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "requirements.txt"
    )
    if os.path.exists(req_file):
        with open(req_file, "r") as f:
            content = f.read()

        if "streamlit" not in content:
            with open(req_file, "a") as f:
                f.write(
                    "\n# GUI dependencies\nstreamlit>=1.12.0\npandas>=1.3.0\nmatplotlib>=3.5.0\ngraphviz>=0.19.1\n"
                )


# Add necessary dependencies
ensure_streamlit_in_requirements()

# Main entry point for direct execution
if __name__ == "__main__":
    st.write("Run this app with: streamlit run gui.py")
