#!/usr/bin/env python3
"""
Script to demonstrate:
1. Fire matmul (a) using FlashAttention
2. When a finishes, fire another matmul (b) and simultaneously 
   fire an all-reduce operation (2 GPU) in another CUDA stream
"""

import torch
import torch.distributed as dist
import torch.nn.functional as F
from torch.cuda import Stream
import time
import os

# Try to import flash attention, fallback to regular attention if not available
try:
    from flash_attn import flash_attn_func
    FLASH_ATTN_AVAILABLE = True
    print("✓ Flash Attention available")
except ImportError:
    FLASH_ATTN_AVAILABLE = False
    print("⚠ Flash Attention not available, using standard attention")

def setup_distributed():
    """Setup distributed environment for 2 GPUs"""
    if 'RANK' in os.environ and 'WORLD_SIZE' in os.environ:
        rank = int(os.environ['RANK'])
        world_size = int(os.environ['WORLD_SIZE'])
        local_rank = int(os.environ['LOCAL_RANK'])
    else:
        # Fallback: use single process with 2 GPUs
        rank = 0
        world_size = 1
        local_rank = 0
        print("⚠ Running in single-process mode. For true 2-GPU all-reduce, use:")
        print("  torchrun --nproc_per_node=2 matmul_allreduce.py")
    
    if torch.cuda.is_available():
        torch.cuda.set_device(local_rank)
        device = torch.device(f'cuda:{local_rank}')
    else:
        device = torch.device('cpu')
        print("⚠ CUDA not available, using CPU")
    
    # Initialize process group if distributed
    if world_size > 1:
        dist.init_process_group(
            backend='nccl',
            init_method='env://',
            world_size=world_size,
            rank=rank
        )
    
    return device, rank, world_size

def flash_attention_matmul(q, k, v):
    """Perform matmul using Flash Attention"""
    if FLASH_ATTN_AVAILABLE:
        # Flash attention expects (batch, seq_len, num_heads, head_dim)
        # and returns (batch, seq_len, num_heads, head_dim)
        return flash_attn_func(q, k, v, dropout_p=0.0, softmax_scale=None, causal=False)
    else:
        # Fallback to standard scaled dot-product attention
        scale = (q.size(-1)) ** -0.5
        attn = torch.matmul(q, k.transpose(-2, -1)) * scale
        attn = F.softmax(attn, dim=-1)
        return torch.matmul(attn, v)

def main():
    device, rank, world_size = setup_distributed()
    
    # Create CUDA streams
    default_stream = torch.cuda.current_stream()
    matmul_stream = Stream()
    allreduce_stream = Stream()
    
    print(f"\n{'='*60}")
    print(f"Device: {device}, Rank: {rank}, World Size: {world_size}")
    print(f"{'='*60}\n")
    
    # Parameters for matmuls
    batch_size = 2
    seq_len = 2048
    num_heads = 8
    head_dim = 64
    hidden_dim = num_heads * head_dim
    
    # Create tensors for matmul (a) - FlashAttention
    print("Creating tensors for matmul (a) - FlashAttention...")
    q_a = torch.randn(batch_size, seq_len, num_heads, head_dim, device=device, dtype=torch.float16)
    k_a = torch.randn(batch_size, seq_len, num_heads, head_dim, device=device, dtype=torch.float16)
    v_a = torch.randn(batch_size, seq_len, num_heads, head_dim, device=device, dtype=torch.float16)
    
    # Synchronize before starting
    torch.cuda.synchronize()
    start_time = time.time()
    
    # ===== STEP 1: Fire matmul (a) using FlashAttention =====
    print(f"[{time.time()-start_time:.4f}s] Firing matmul (a) - FlashAttention...")
    with torch.cuda.stream(default_stream):
        result_a = flash_attention_matmul(q_a, k_a, v_a)
    
    # Wait for matmul (a) to complete
    default_stream.synchronize()
    time_a_finish = time.time()
    print(f"[{time_a_finish-start_time:.4f}s] Matmul (a) completed")
    
    # ===== STEP 2: Fire matmul (b) and all-reduce in parallel =====
    print(f"[{time.time()-start_time:.4f}s] Firing matmul (b) and all-reduce in parallel...")
    
    # Create tensors for matmul (b)
    x_b = torch.randn(batch_size, seq_len, hidden_dim, device=device, dtype=torch.float16)
    w_b = torch.randn(hidden_dim, hidden_dim, device=device, dtype=torch.float16)
    
    # Create tensor for all-reduce
    allreduce_tensor = torch.randn(1024, 1024, device=device, dtype=torch.float16)
    
    # Fire matmul (b) in matmul_stream
    with torch.cuda.stream(matmul_stream):
        result_b = torch.matmul(x_b, w_b)
    
    # Fire all-reduce in allreduce_stream (only if world_size > 1)
    if world_size > 1:
        with torch.cuda.stream(allreduce_stream):
            dist.all_reduce(allreduce_tensor, op=dist.ReduceOp.SUM)
            allreduce_tensor = allreduce_tensor / world_size  # Average
    else:
        # Simulate all-reduce with a dummy operation
        with torch.cuda.stream(allreduce_stream):
            # Just do some computation to simulate all-reduce
            allreduce_tensor = allreduce_tensor * 2.0
    
    # Wait for both to complete
    matmul_stream.synchronize()
    allreduce_stream.synchronize()
    
    end_time = time.time()
    print(f"[{end_time-start_time:.4f}s] Matmul (b) and all-reduce completed")
    
    print(f"\n{'='*60}")
    print(f"Total execution time: {end_time-start_time:.4f}s")
    print(f"Time for matmul (a): {time_a_finish-start_time:.4f}s")
    print(f"Time for matmul (b) + all-reduce: {end_time-time_a_finish:.4f}s")
    print(f"{'='*60}\n")
    
    # Cleanup
    if world_size > 1:
        dist.destroy_process_group()

if __name__ == "__main__":
    main()

