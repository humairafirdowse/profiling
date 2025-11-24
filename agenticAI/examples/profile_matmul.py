"""
Example: Using the agent to profile a distributed PyTorch script with nsys,
analyze bottlenecks, and get optimization suggestions.

This example demonstrates:
1. Running a Python script (matmul_allreduce.py) with nsys profiling
2. Converting nsys report to SQLite
3. Analyzing the SQLite database for bottlenecks
4. Getting suggestions for optimization
"""
import asyncio
import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from agenticAI import CodingAgent


async def main():
    """Example profiling workflow"""
    
    # Initialize agent with workspace
    workspace = Path(__file__).parent.parent / "workspace"
    agent = CodingAgent(workspace_path=str(workspace))
    
    print("=" * 60)
    print("GPU Profiling Example with nsys")
    print("=" * 60)
    print()
    
    # Path to the script to profile (relative to workspace or absolute)
    script_path = "/root/profiling/agenticAI/examples/matmul_allreduce.py"  # Adjust path as needed
    
    # Task 1: Profile the script with nsys
    print("Step 1: Profiling script with nsys...")
    task1 = f"""
    Use the profile_with_nsys tool to profile the script at {script_path}.
    Use these parameters:
      - output_name='matmul_profile'
      - launcher='torchrun'
      - nproc_per_node=2
      - launcher_args='--standalone'
      - cuda_visible_devices='0,1'
      - nsys_args='--trace=cuda,nvtx,osrt --force-overwrite=true'
    """
    
    result1 = await agent.run(task1, max_iterations=1)
    
    if result1["success"]:
        print("✅ Profiling completed successfully")
        # Extract SQLite DB path from results
        sqlite_path = None
        for action_result in result1.get("results", []):
            result_data = action_result.get("result", {}).get("result", {})
            if isinstance(result_data, dict) and "sqlite_db" in result_data:
                sqlite_path = result_data["sqlite_db"]
                break
        
        if sqlite_path:
            print(f"   SQLite database: {sqlite_path}")
            
            # Task 2: Analyze the SQLite database
            print("\nStep 2: Analyzing SQLite database for bottlenecks...")
            task2 = f"""
            Use the analyze_nsys_sqlite tool to analyze the database at {sqlite_path}.
            Perform a full analysis (analysis_type='all') to find:
            - Computation bottlenecks (long-running CUDA kernels)
            - Communication bottlenecks (NCCL operations)
            - Overlap opportunities between compute and communication
            - Timeline of events
            """
            
            result2 = await agent.run(task2, max_iterations=1)
            
            if result2["success"]:
                print("✅ Analysis completed successfully")
                
                # Extract and display suggestions
                for action_result in result2.get("results", []):
                    result_data = action_result.get("result", {}).get("result", {})
                    if isinstance(result_data, dict) and "analysis" in result_data:
                        analysis = result_data["analysis"]
                        suggestions = analysis.get("suggestions", [])
                        
                        if suggestions:
                            print("\n" + "=" * 60)
                            print("Optimization Suggestions:")
                            print("=" * 60)
                            for i, suggestion in enumerate(suggestions, 1):
                                print(f"{i}. {suggestion}")
                            
                            # Display key findings
                            if "computation_bottlenecks" in analysis:
                                bottlenecks = analysis["computation_bottlenecks"]
                                if isinstance(bottlenecks, list) and bottlenecks:
                                    print("\nTop Computation Bottlenecks:")
                                    for b in bottlenecks[:5]:
                                        print(f"   - {b.get('kernel', 'N/A')}: {b.get('duration_ms', 0):.2f}ms")
                            
                            if "communication_bottlenecks" in analysis:
                                comm_bottlenecks = analysis["communication_bottlenecks"]
                                if isinstance(comm_bottlenecks, list) and comm_bottlenecks:
                                    print("\nTop Communication Bottlenecks:")
                                    for c in comm_bottlenecks[:5]:
                                        print(f"   - {c.get('operation', 'N/A')}: {c.get('duration_ms', 0):.2f}ms")
                            
                            if "overlap_analysis" in analysis:
                                overlap = analysis["overlap_analysis"]
                                if isinstance(overlap, list):
                                    print(f"\nOverlap Events Found: {len(overlap)}")
                                elif isinstance(overlap, dict):
                                    print(f"\nOverlap Analysis:")
                                    print(f"   Total Kernel Time: {overlap.get('total_kernel_time_ms', 0):.2f}ms")
                                    print(f"   Total Comm Time: {overlap.get('total_comm_time_ms', 0):.2f}ms")
            else:
                print(f"❌ Analysis failed: {result2.get('message', 'Unknown error')}")
        else:
            print("⚠️  Could not find SQLite database path in results")
    else:
        print(f"❌ Profiling failed: {result1.get('message', 'Unknown error')}")
    
    print("\n" + "=" * 60)
    print("Example completed")
    print("=" * 60)


if __name__ == "__main__":
    # Note: This example requires:
    # 1. NVIDIA Nsight Systems (nsys) installed
    # 2. CUDA-enabled GPU
    # 3. PyTorch with distributed support
    # 4. The matmul_allreduce.py script in the parent directory
    
    print("Note: This example requires nsys and CUDA setup.")
    print("Make sure matmul_allreduce.py is accessible.\n")
    
    asyncio.run(main())


