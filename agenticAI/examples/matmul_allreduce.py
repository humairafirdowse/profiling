import os
import torch
import torch.distributed as dist
import time

def setup():
    """Initialize the distributed environment."""
    dist.init_process_group("nccl")
    rank = dist.get_rank()
    world_size = dist.get_world_size()
    torch.cuda.set_device(rank)
    return rank, world_size

def cleanup():
    """Clean up the distributed environment."""
    dist.destroy_process_group()


# ============================================================================
# Example 1: NO OVERLAP - Sequential Compute then Communication
# ============================================================================
def no_overlap_matmul(rank, world_size, size=4096):
    """
    Computation and communication happen sequentially - no overlap.
    Pattern: Compute -> Wait -> Communicate -> Wait
    """
    # setup() was already called in main()

    # Create matrices on each GPU
    A = torch.randn(size, size, device=f'cuda:{rank}')
    B = torch.randn(size, size, device=f'cuda:{rank}')
    
    print(f"[Rank {rank}] Starting NO OVERLAP example...")
    start = time.time()
    
    # Step 1: Do ALL computation first (blocking)
    print(f"[Rank {rank}] Computing matmul...")
    C = torch.matmul(A, B)
    torch.cuda.synchronize()  # Wait for computation to finish
    
    # Step 2: Then do communication (blocking)
    print(f"[Rank {rank}] Starting communication...")
    dist.all_reduce(C, op=dist.ReduceOp.SUM)
    torch.cuda.synchronize()  # Wait for communication to finish
    
    end = time.time()
    print(f"[Rank {rank}] NO OVERLAP completed in {end-start:.3f}s")
    
    return C


# ============================================================================
# Example 2: WITH OVERLAP - Interleaved Compute and Communication
# ============================================================================

def overlap_matmul(rank, world_size, size=4096, num_chunks=4):
    """
    True overlap of matmul compute and all_reduce communication using chunking
    and separate CUDA streams.

    Pattern per chunk:
      compute_stream:  C_i = A_i @ B
      comm_stream:     wait for compute_stream(C_i), all_reduce(C_i)
    """
    device = torch.device(f"cuda:{rank}")

    # Allocate A, B, and full C ahead of time
    A = torch.randn(size, size, device=device)
    B = torch.randn(size, size, device=device)
    C = torch.empty(size, size, device=device)

    # Two streams: one for compute, one for comm
    compute_stream = torch.cuda.default_stream(device)
    comm_stream = torch.cuda.Stream(device=device)

    print(f"[Rank {rank}] Starting TRUE OVERLAP example...")
    start = time.time()

    chunk_size = size // num_chunks
    handles = []

    for i in range(num_chunks):
        start_idx = i * chunk_size
        end_idx = (i + 1) * chunk_size

        A_chunk = A[start_idx:end_idx, :]
        C_chunk = C[start_idx:end_idx, :]

        # 1) Launch matmul for this chunk on compute_stream
        with torch.cuda.stream(compute_stream):
            # C_chunk = A_chunk @ B  (out= to avoid new allocation)
            C_chunk[:] = torch.matmul(A_chunk, B)

        # 2) On comm_stream, wait until this chunk's compute is done,
        #    then launch async all_reduce for this chunk.
        with torch.cuda.stream(comm_stream):
            # this makes comm_stream see all work in compute_stream up to now
            comm_stream.wait_stream(compute_stream)

            handle = dist.all_reduce(C_chunk, op=dist.ReduceOp.SUM, async_op=True)
            handles.append(handle)

        # 3) Loop continues: next iteration will enqueue compute for next chunk
        #    on compute_stream, which can overlap with ongoing NCCL on comm_stream.

    # Wait for all all_reduce ops to finish
    for h in handles:
        h.wait()

    # Optional: synchronize both streams before measuring end time
    torch.cuda.synchronize(device)

    end = time.time()
    print(f"[Rank {rank}] TRUE OVERLAP completed in {end - start:.3f}s")

    return C

# ============================================================================
# Example 3: Another OVERLAP pattern - Pipeline style
# ============================================================================
def pipeline_overlap(rank, world_size, size=4096):
    """
    Pipeline-style overlap: compute -> start comm -> compute more while comm runs.
    """
    # setup() was already called in main()

    A = torch.randn(size, size, device=f'cuda:{rank}')
    B = torch.randn(size, size, device=f'cuda:{rank}')
    X = torch.randn(size, size, device=f'cuda:{rank}')
    
    print(f"[Rank {rank}] Starting PIPELINE OVERLAP example...")
    start = time.time()
    
    # First computation
    C = torch.matmul(A, B)
    
    # Start async communication (non-blocking!)
    handle = dist.all_reduce(C, op=dist.ReduceOp.SUM, async_op=True)
    
    # While C is being communicated, do MORE computation!
    print(f"[Rank {rank}] Computing additional work while communicating...")
    D = torch.matmul(X, X)  # This overlaps with the all_reduce!
    D = torch.matmul(D, D)  # More work...
    
    # Wait for communication to finish
    handle.wait()
    torch.cuda.synchronize()
    
    end = time.time()
    print(f"[Rank {rank}] PIPELINE OVERLAP completed in {end-start:.3f}s")


# ============================================================================
# Main execution function
# ============================================================================
def main():
    """
    To run this code, use torchrun:
    
    torchrun --nproc_per_node=2 this_script.py
    """
    # 1. Initialize process group + set device
    rank, world_size = setup()
    
    print(f"\n{'='*60}")
    print(f"Running on Rank {rank} of {world_size}")
    print(f"{'='*60}\n")
    
    # 2. Run the examples (process group already initialized)
    #no_overlap_matmul(rank, world_size, size=4096)
    overlap_matmul(rank, world_size, size=4096, num_chunks=4)
    # pipeline_overlap(rank, world_size, size=4096)
    
    # 3. Clean up
    cleanup()


if __name__ == "__main__":
    main()
