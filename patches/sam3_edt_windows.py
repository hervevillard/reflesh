# Copyright (c) Meta Platforms, Inc. and affiliates. All Rights Reserved
# pyre-unsafe
#
# ArtSegment patch — Windows triton workaround
# Applied by patch_sam3.py after every sam3 install.
#
# triton has no Windows distribution. This file guards the import and falls back
# to cv2.distanceTransform, which is semantically identical (same algorithm,
# same output — the sam3 docstring says so explicitly).

"""Triton kernel for euclidean distance transform (EDT), with cv2 fallback for Windows."""

import torch

try:
    import triton
    import triton.language as tl
    _TRITON_AVAILABLE = True
except ImportError:
    _TRITON_AVAILABLE = False
    triton = None
    tl = None


if _TRITON_AVAILABLE:
    @triton.jit
    def edt_kernel(inputs_ptr, outputs_ptr, v, z, height, width, horizontal: tl.constexpr):
        batch_id = tl.program_id(axis=0)
        if horizontal:
            row_id = tl.program_id(axis=1)
            block_start = (batch_id * height * width) + row_id * width
            length = width
            stride = 1
        else:
            col_id = tl.program_id(axis=1)
            block_start = (batch_id * height * width) + col_id
            length = height
            stride = width

        k = 0
        for q in range(1, length):
            cur_input = tl.load(inputs_ptr + block_start + (q * stride))
            r = tl.load(v + block_start + (k * stride))
            z_k = tl.load(z + block_start + (k * stride))
            previous_input = tl.load(inputs_ptr + block_start + (r * stride))
            s = (cur_input - previous_input + q * q - r * r) / (q - r) / 2

            while s <= z_k and k - 1 >= 0:
                k = k - 1
                r = tl.load(v + block_start + (k * stride))
                z_k = tl.load(z + block_start + (k * stride))
                previous_input = tl.load(inputs_ptr + block_start + (r * stride))
                s = (cur_input - previous_input + q * q - r * r) / (q - r) / 2

            k = k + 1
            tl.store(v + block_start + (k * stride), q)
            tl.store(z + block_start + (k * stride), s)
            if k + 1 < length:
                tl.store(z + block_start + ((k + 1) * stride), 1e9)

        k = 0
        for q in range(length):
            while (
                k + 1 < length
                and tl.load(
                    z + block_start + ((k + 1) * stride), mask=(k + 1) < length, other=q
                )
                < q
            ):
                k += 1
            r = tl.load(v + block_start + (k * stride))
            d = q - r
            old_value = tl.load(inputs_ptr + block_start + (r * stride))
            tl.store(outputs_ptr + block_start + (q * stride), old_value + d * d)


def edt_triton(data: torch.Tensor) -> torch.Tensor:
    """
    Euclidean Distance Transform: L2 distance from each pixel to the nearest zero pixel.
    Equivalent to a batched cv2.distanceTransform(input, cv2.DIST_L2, 0).

    Args:
        data: (B, H, W) bool/uint8 tensor

    Returns:
        (B, H, W) float32 tensor of L2 distances
    """
    assert data.dim() == 3

    if not _TRITON_AVAILABLE:
        # triton has no Windows wheels — use cv2 fallback (same result, CPU)
        import cv2
        import numpy as np
        result = torch.zeros(data.shape, dtype=torch.float32)
        data_np = data.cpu().numpy().astype(np.uint8)
        for i in range(data.shape[0]):
            result[i] = torch.from_numpy(
                cv2.distanceTransform(data_np[i], cv2.DIST_L2, 0)
            )
        return result.to(device=data.device)

    assert data.is_cuda
    B, H, W = data.shape
    data = data.contiguous()

    output = torch.where(data, 1e18, 0.0)
    assert output.is_contiguous()

    parabola_loc = torch.zeros(B, H, W, dtype=torch.uint32, device=data.device)
    parabola_inter = torch.empty(B, H, W, dtype=torch.float, device=data.device)
    parabola_inter[:, :, 0] = -1e18
    parabola_inter[:, :, 1] = 1e18

    edt_kernel[(B, H)](
        output.clone(), output, parabola_loc, parabola_inter, H, W, horizontal=True,
    )

    parabola_loc.zero_()
    parabola_inter[:, :, 0] = -1e18
    parabola_inter[:, :, 1] = 1e18

    edt_kernel[(B, W)](
        output.clone(), output, parabola_loc, parabola_inter, H, W, horizontal=False,
    )
    return output.sqrt()
