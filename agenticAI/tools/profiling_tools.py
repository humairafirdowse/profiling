"""
Profiling tools for GPU performance analysis using NVIDIA Nsight Systems (nsys).
Supports running scripts with nsys, converting to SQLite, and analyzing bottlenecks.
"""
import os
import subprocess
import sqlite3
import json
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional
from .base import Tool, ToolParameter


class ProfileWithNsysTool(Tool):
    """Run a Python script with nsys profiling and convert to SQLite database"""
    
    def __init__(self):
        super().__init__(
            name="profile_with_nsys",
            description="Run a Python script with NVIDIA Nsight Systems (nsys) profiling and convert the report to SQLite format for analysis. Returns the path to the SQLite database.",
            parameters=[
                ToolParameter(
                    name="script_path",
                    type="string",
                    description="Path to the Python script to profile (e.g., matmul_allreduce.py)",
                    required=True
                ),
                ToolParameter(
                    name="output_name",
                    type="string",
                    description="Base name for output files (nsys report and SQLite DB). Defaults to script name without extension.",
                    required=False,
                    default=None
                ),
                ToolParameter(
                    name="nsys_args",
                    type="string",
                    description="Additional arguments to pass to nsys (e.g., '--trace=cuda,nvtx' or '--force-overwrite=true'). Default: '--trace=cuda,nvtx,osrt'",
                    required=False,
                    default="--trace=cuda,nvtx,osrt"
                ),
                ToolParameter(
                    name="script_args",
                    type="string",
                    description="Arguments to pass to the target script (e.g., '--size 8192'). Default: empty",
                    required=False,
                    default=""
                ),
                ToolParameter(
                    name="launcher",
                    type="string",
                    description="Launcher command to run the script. Supported shortcuts: 'python', 'torchrun'. "
                                "Custom launchers may be provided as full commands. Default: 'python'.",
                    required=False,
                    default="python"
                ),
                ToolParameter(
                    name="launcher_args",
                    type="string",
                    description="Additional arguments to pass to the launcher (parsed with shlex).",
                    required=False,
                    default=""
                ),
                ToolParameter(
                    name="nproc_per_node",
                    type="integer",
                    description="Number of processes per node when using torchrun. Ignored otherwise.",
                    required=False,
                    default=1
                ),
                ToolParameter(
                    name="cuda_visible_devices",
                    type="string",
                    description="Optional CUDA_VISIBLE_DEVICES value (e.g., '0,1') to limit GPUs.",
                    required=False,
                    default=None
                ),
                ToolParameter(
                    name="env_vars",
                    type="string",
                    description="JSON object string of environment variables to set before launching "
                                "(e.g., '{\"MASTER_ADDR\":\"localhost\"}').",
                    required=False,
                    default=""
                ),
            ]
        )
    
    async def execute(
        self,
        script_path: str,
        output_name: Optional[str] = None, 
        nsys_args: str = "--trace=cuda,nvtx,osrt",
        script_args: str = "",
        launcher: str = "python",
        launcher_args: str = "",
        nproc_per_node: int = 1,
        cuda_visible_devices: Optional[str] = None,
        env_vars: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute profiling workflow:
        1. Run script with nsys to generate .nsys-rep file
        2. Convert .nsys-rep to SQLite using nsys export
        3. Return path to SQLite database
        """
        try:
            workspace = Path(kwargs.get("workspace_path", "."))
            script_path_obj = Path(script_path)
            
            if not script_path_obj.is_absolute():
                script_path_obj = workspace / script_path_obj
            
            if not script_path_obj.exists():
                return {"success": False, "error": f"Script not found: {script_path}"}
            
            # Determine output names
            if output_name is None:
                output_name = script_path_obj.stem
            
            output_dir = script_path_obj.parent
            nsys_rep_file = output_dir / f"{output_name}.nsys-rep"
            sqlite_db_file = output_dir / f"{output_name}.sqlite"
            
            # Step 1: Run with nsys
            # Check if nsys is available
            try:
                subprocess.run(["nsys", "--version"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                return {"success": False, "error": "nsys command not found. Please install NVIDIA Nsight Systems."}
            
            # Build nsys command
            nsys_cmd: List[str] = [
                "nsys", "profile",
                "--output", str(nsys_rep_file),
            ]
            
            # Parse additional nsys args
            if nsys_args:
                nsys_cmd.extend(shlex.split(nsys_args))
            
            # Build launcher command (python / torchrun / custom)
            launcher = launcher.strip() or "python"
            launcher_cmd: List[str] = []
            if launcher in {"python", "python3"}:
                launcher_cmd = [launcher]
            elif launcher == "torchrun":
                launcher_cmd = ["torchrun", f"--nproc_per_node={max(1, int(nproc_per_node))}"]
            else:
                launcher_cmd = shlex.split(launcher)
            
            if launcher_args:
                launcher_cmd.extend(shlex.split(launcher_args))
            
            launcher_cmd.append(str(script_path_obj))
            
            if script_args:
                launcher_cmd.extend(shlex.split(script_args))
            
            nsys_cmd.extend(launcher_cmd)
            
            # Prepare environment for subprocess
            env = os.environ.copy()
            if cuda_visible_devices:
                env["CUDA_VISIBLE_DEVICES"] = cuda_visible_devices
            if env_vars:
                try:
                    extra_env = json.loads(env_vars)
                    if isinstance(extra_env, dict):
                        env.update({str(k): str(v) for k, v in extra_env.items()})
                    else:
                        return {"success": False, "error": "env_vars must be a JSON object string"}
                except json.JSONDecodeError:
                    return {"success": False, "error": "env_vars must be a JSON object string"}
            
            print(f"Running: {' '.join(nsys_cmd)}")
            result = subprocess.run(
                nsys_cmd,
                capture_output=True,
                text=True,
                cwd=str(workspace),
                env=env
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"nsys profiling failed: {result.stderr}",
                    "stdout": result.stdout
                }
            
            if not nsys_rep_file.exists():
                return {"success": False, "error": f"nsys report file not created: {nsys_rep_file}"}
            
            # Step 2: Convert to SQLite
            export_cmd = [
                "nsys", "export",
                "--type", "sqlite",
                "--output", str(sqlite_db_file),
                str(nsys_rep_file)
            ]
            
            print(f"Converting to SQLite: {' '.join(export_cmd)}")
            export_result = subprocess.run(
                export_cmd,
                capture_output=True,
                text=True,
                cwd=str(workspace)
            )
            
            if export_result.returncode != 0:
                return {
                    "success": False,
                    "error": f"SQLite conversion failed: {export_result.stderr}",
                    "stdout": export_result.stdout
                }
            
            if not sqlite_db_file.exists():
                return {"success": False, "error": f"SQLite database not created: {sqlite_db_file}"}
            
            return {
                "success": True,
                "result": {
                    "sqlite_db": str(sqlite_db_file),
                    "nsys_rep": str(nsys_rep_file),
                    "script_path": str(script_path_obj),
                    "output_name": output_name
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Profiling failed: {str(e)}"}


class AnalyzeNsysSqliteTool(Tool):
    """Analyze nsys SQLite database to find computation and communication bottlenecks"""
    
    def __init__(self):
        super().__init__(
            name="analyze_nsys_sqlite",
            description="Analyze an nsys SQLite database to identify computation and communication bottlenecks, overlap opportunities, and suggest optimizations.",
            parameters=[
                ToolParameter(
                    name="sqlite_db_path",
                    type="string",
                    description="Path to the nsys SQLite database file",
                    required=True
                ),
                ToolParameter(
                    name="analysis_type",
                    type="string",
                    description="Type of analysis: 'bottlenecks', 'overlap', 'timeline', or 'all'. Default: 'all'",
                    required=False,
                    default="all"
                )
            ]
        )
    
    async def execute(self, sqlite_db_path: str, analysis_type: str = "all", **kwargs) -> Dict[str, Any]:
        """
        Analyze the SQLite database with SQL queries to find:
        - Computation bottlenecks (long-running CUDA kernels)
        - Communication bottlenecks (NCCL operations)
        - Overlap opportunities (compute vs comm timing)
        - Suggestions for optimization
        """
        try:
            workspace = Path(kwargs.get("workspace_path", "."))
            db_path = Path(sqlite_db_path)
            
            if not db_path.is_absolute():
                db_path = workspace / db_path
            
            if not db_path.exists():
                return {"success": False, "error": f"SQLite database not found: {sqlite_db_path}"}
            
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            analysis_results = {}
            
            # Get database schema info
            tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_names = [row[0] for row in tables]
            
            # Common nsys tables: CUPTI_ACTIVITY_KIND_KERNEL, CUPTI_ACTIVITY_KIND_RUNTIME, etc.
            # We'll query for kernels, memcpy, and runtime activities
            
            if analysis_type in ["bottlenecks", "all"]:
                # Find longest CUDA kernels (computation bottlenecks)
                kernel_query = """
                SELECT 
                    shortName as kernel_name,
                    duration/1e6 as duration_ms,
                    start/1e9 as start_time_s,
                    end/1e9 as end_time_s,
                    gridX, gridY, gridZ,
                    blockX, blockY, blockZ
                FROM CUPTI_ACTIVITY_KIND_KERNEL
                ORDER BY duration DESC
                LIMIT 20
                """
                
                try:
                    kernels = cursor.execute(kernel_query).fetchall()
                    analysis_results["computation_bottlenecks"] = [
                        {
                            "kernel": row["kernel_name"],
                            "duration_ms": row["duration_ms"],
                            "start_time_s": row["start_time_s"],
                            "end_time_s": row["end_time_s"],
                            "grid": f"{row['gridX']}x{row['gridY']}x{row['gridZ']}",
                            "block": f"{row['blockX']}x{row['blockY']}x{row['blockZ']}"
                        }
                        for row in kernels
                    ]
                except sqlite3.OperationalError as e:
                    analysis_results["computation_bottlenecks"] = f"Query failed: {str(e)}"
            
            if analysis_type in ["bottlenecks", "all"]:
                # Find NCCL operations (communication bottlenecks)
                # NCCL operations might be in runtime or stringId tables
                nccl_query = """
                SELECT 
                    shortName as name,
                    duration/1e6 as duration_ms,
                    start/1e9 as start_time_s,
                    end/1e9 as end_time_s
                FROM CUPTI_ACTIVITY_KIND_RUNTIME
                WHERE shortName LIKE '%nccl%' OR shortName LIKE '%NCCL%' OR shortName LIKE '%all_reduce%'
                ORDER BY duration DESC
                LIMIT 20
                """
                
                try:
                    nccl_ops = cursor.execute(nccl_query).fetchall()
                    analysis_results["communication_bottlenecks"] = [
                        {
                            "operation": row["name"],
                            "duration_ms": row["duration_ms"],
                            "start_time_s": row["start_time_s"],
                            "end_time_s": row["end_time_s"]
                        }
                        for row in nccl_ops
                    ]
                except sqlite3.OperationalError as e:
                    # Try alternative query
                    try:
                        # Look for stringId references
                        string_query = """
                        SELECT name FROM StringIds WHERE name LIKE '%nccl%' OR name LIKE '%NCCL%'
                        """
                        string_ids = cursor.execute(string_query).fetchall()
                        analysis_results["communication_bottlenecks"] = {
                            "note": "Found NCCL-related strings",
                            "strings": [row["name"] for row in string_ids]
                        }
                    except:
                        analysis_results["communication_bottlenecks"] = f"Query failed: {str(e)}"
            
            if analysis_type in ["overlap", "all"]:
                # Analyze overlap between computation and communication
                # Find time windows where kernels and NCCL ops overlap
                overlap_query = """
                WITH kernel_times AS (
                    SELECT 
                        start/1e9 as k_start,
                        end/1e9 as k_end,
                        shortName as k_name,
                        duration/1e6 as k_duration_ms
                    FROM CUPTI_ACTIVITY_KIND_KERNEL
                ),
                comm_times AS (
                    SELECT 
                        start/1e9 as c_start,
                        end/1e9 as c_end,
                        shortName as c_name,
                        duration/1e6 as c_duration_ms
                    FROM CUPTI_ACTIVITY_KIND_RUNTIME
                    WHERE shortName LIKE '%nccl%' OR shortName LIKE '%NCCL%' OR shortName LIKE '%all_reduce%'
                )
                SELECT 
                    k.k_name,
                    k.k_start,
                    k.k_end,
                    c.c_name,
                    c.c_start,
                    c.c_end,
                    CASE 
                        WHEN c.c_start <= k.k_end AND c.c_end >= k.k_start THEN 'OVERLAP'
                        ELSE 'NO_OVERLAP'
                    END as overlap_status,
                    CASE 
                        WHEN c.c_start <= k.k_end AND c.c_end >= k.k_start THEN
                            LEAST(k.k_end, c.c_end) - GREATEST(k.k_start, c.c_start)
                        ELSE 0
                    END as overlap_duration_s
                FROM kernel_times k
                CROSS JOIN comm_times c
                WHERE overlap_status = 'OVERLAP'
                ORDER BY overlap_duration_s DESC
                LIMIT 20
                """
                
                try:
                    overlaps = cursor.execute(overlap_query).fetchall()
                    analysis_results["overlap_analysis"] = [
                        {
                            "kernel": row["k_name"],
                            "kernel_time": f"{row['k_start']:.3f}s - {row['k_end']:.3f}s",
                            "comm_operation": row["c_name"],
                            "comm_time": f"{row['c_start']:.3f}s - {row['c_end']:.3f}s",
                            "overlap_duration_s": row["overlap_duration_s"],
                            "status": row["overlap_status"]
                        }
                        for row in overlaps
                    ]
                except sqlite3.OperationalError as e:
                    # Simplified overlap analysis
                    try:
                        # Get total kernel time and total comm time
                        total_kernel_time = cursor.execute("""
                            SELECT SUM(duration)/1e6 as total_ms 
                            FROM CUPTI_ACTIVITY_KIND_KERNEL
                        """).fetchone()
                        
                        total_comm_time = cursor.execute("""
                            SELECT SUM(duration)/1e6 as total_ms 
                            FROM CUPTI_ACTIVITY_KIND_RUNTIME
                            WHERE shortName LIKE '%nccl%' OR shortName LIKE '%NCCL%'
                        """).fetchone()
                        
                        analysis_results["overlap_analysis"] = {
                            "total_kernel_time_ms": total_kernel_time["total_ms"] if total_kernel_time else 0,
                            "total_comm_time_ms": total_comm_time["total_ms"] if total_comm_time else 0,
                            "note": "Detailed overlap query not available, showing totals"
                        }
                    except:
                        analysis_results["overlap_analysis"] = f"Query failed: {str(e)}"
            
            if analysis_type in ["timeline", "all"]:
                # Get timeline of major events
                timeline_query = """
                SELECT 
                    'kernel' as type,
                    shortName as name,
                    start/1e9 as time_s,
                    duration/1e6 as duration_ms
                FROM CUPTI_ACTIVITY_KIND_KERNEL
                UNION ALL
                SELECT 
                    'runtime' as type,
                    shortName as name,
                    start/1e9 as time_s,
                    duration/1e6 as duration_ms
                FROM CUPTI_ACTIVITY_KIND_RUNTIME
                WHERE shortName LIKE '%nccl%' OR shortName LIKE '%NCCL%' OR shortName LIKE '%all_reduce%'
                ORDER BY time_s
                LIMIT 100
                """
                
                try:
                    timeline = cursor.execute(timeline_query).fetchall()
                    analysis_results["timeline"] = [
                        {
                            "type": row["type"],
                            "name": row["name"],
                            "time_s": row["time_s"],
                            "duration_ms": row["duration_ms"]
                        }
                        for row in timeline
                    ]
                except sqlite3.OperationalError as e:
                    analysis_results["timeline"] = f"Query failed: {str(e)}"
            
            # Generate suggestions based on analysis
            suggestions = self._generate_suggestions(analysis_results)
            analysis_results["suggestions"] = suggestions
            
            conn.close()
            
            return {
                "success": True,
                "result": {
                    "database_path": str(db_path),
                    "tables_found": table_names,
                    "analysis": analysis_results
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Analysis failed: {str(e)}"}
    
    def _generate_suggestions(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate optimization suggestions based on analysis results"""
        suggestions = []
        
        # Check computation bottlenecks
        if "computation_bottlenecks" in analysis:
            bottlenecks = analysis["computation_bottlenecks"]
            if isinstance(bottlenecks, list) and bottlenecks:
                longest_kernel = bottlenecks[0]
                if longest_kernel.get("duration_ms", 0) > 100:  # > 100ms
                    suggestions.append(
                        f"Longest kernel '{longest_kernel['kernel']}' takes {longest_kernel['duration_ms']:.2f}ms. "
                        "Consider: kernel fusion, better memory access patterns, or reducing problem size."
                    )
        
        # Check communication bottlenecks
        if "communication_bottlenecks" in analysis:
            comm_bottlenecks = analysis["communication_bottlenecks"]
            if isinstance(comm_bottlenecks, list) and comm_bottlenecks:
                longest_comm = comm_bottlenecks[0]
                if longest_comm.get("duration_ms", 0) > 50:  # > 50ms
                    suggestions.append(
                        f"Long communication operation '{longest_comm['operation']}' takes {longest_comm['duration_ms']:.2f}ms. "
                        "Consider: overlapping communication with computation using CUDA streams, or using gradient compression."
                    )
        
        # Check overlap opportunities
        if "overlap_analysis" in analysis:
            overlap = analysis["overlap_analysis"]
            if isinstance(overlap, list):
                if not overlap:
                    suggestions.append(
                        "No overlap detected between computation and communication. "
                        "Consider implementing pipelined execution with separate CUDA streams for compute and communication."
                    )
                else:
                    total_overlap = sum(o.get("overlap_duration_s", 0) for o in overlap)
                    if total_overlap > 0:
                        suggestions.append(
                            f"Found {len(overlap)} overlapping operations totaling {total_overlap*1000:.2f}ms. "
                            "This is good! Consider increasing overlap by chunking operations and using async communication."
                        )
            elif isinstance(overlap, dict):
                kernel_time = overlap.get("total_kernel_time_ms", 0)
                comm_time = overlap.get("total_comm_time_ms", 0)
                if kernel_time > 0 and comm_time > 0:
                    sequential_time = kernel_time + comm_time
                    potential_savings = min(kernel_time, comm_time)
                    suggestions.append(
                        f"Sequential execution time: {sequential_time:.2f}ms (compute: {kernel_time:.2f}ms, comm: {comm_time:.2f}ms). "
                        f"Potential savings with full overlap: {potential_savings:.2f}ms ({potential_savings/sequential_time*100:.1f}% reduction)."
                    )
        
        if not suggestions:
            suggestions.append("No specific bottlenecks identified. Profile looks good!")
        
        return suggestions


class ProfilingTools:
    """Collection of profiling tools"""
    
    @staticmethod
    def register_all(registry: 'ToolRegistry', workspace_path: str = "."):
        """Register all profiling tools with workspace context"""
        tools = [
            ProfileWithNsysTool(),
            AnalyzeNsysSqliteTool()
        ]
        
        def create_wrapper(orig_exec, ws_path):
            """Factory function to create a properly closed wrapper"""
            async def wrapped_execute(**kwargs):
                """Wrapper that injects workspace_path"""
                kwargs["workspace_path"] = ws_path
                return await orig_exec(**kwargs)
            return wrapped_execute
        
        for tool in tools:
            wrapped = create_wrapper(tool.execute, workspace_path)
            object.__setattr__(tool, 'execute', wrapped)
            registry.register(tool)


