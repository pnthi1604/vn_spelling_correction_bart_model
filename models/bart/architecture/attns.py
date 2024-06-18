import torch
import torch.nn as nn
import math
    
class MutilheadAttention(nn.Module):
    def __init__(
        self,
        embed_dim: int,
        num_heads: int,
        dropout: float=0.0,
        bias: bool=True,
    ):
        super().__init__()
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        self.scaling = self.head_dim ** -0.5

        self.dropout = nn.Dropout(dropout)
        self.k_proj = nn.Linear(embed_dim, embed_dim, bias=bias)
        self.v_proj = nn.Linear(embed_dim, embed_dim, bias=bias)
        self.q_proj = nn.Linear(embed_dim, embed_dim, bias=bias)
        self.out_proj = nn.Linear(embed_dim, embed_dim, bias=bias)

    def _shape(
        self,
        tensor: torch.Tensor,
        seq_len: int,
        bsz: int,
    ):
        return tensor.view(bsz, seq_len, self.num_heads, self.head_dim).transpose(1, 2).contiguous()
    
    def scaled_dot_product_attention(
        self,
        query: torch.Tensor,
        key: torch.Tensor,
        value: torch.Tensor,
        mask: torch.Tensor,
        dropout: nn.Dropout=None,
    ) -> torch.Tensor:
        d_k = query.size(-1)
        scores = torch.matmul(query, key.transpose(-2, -1)) / math.sqrt(d_k)
        if mask is not None:
            scores = scores.masked_fill(mask == 0, -1e9)
        p_attn = nn.functional.softmax(scores, dim=-1)
        if dropout is not None:
            p_attn = dropout(p_attn)
        return torch.matmul(p_attn, value)

class MultiheadScaledDotProductAttention(MutilheadAttention):
    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)
    
    def forward(
        self,
        hidden_states: torch.Tensor,
        key_value_states: torch.Tensor=None,
        attention_mask: torch.Tensor=None,
        layer_head_mask: torch.Tensor=None,
    ):
        bsz, tgt_len, embed_dim = hidden_states.size()
        assert embed_dim == self.embed_dim, f"Hidden states have embed_dim {embed_dim}, expected {self.embed_dim}"

        query_states = self.q_proj(hidden_states) * self.scaling
        if key_value_states is None:
            key_states = self.k_proj(hidden_states)
            value_states = self.v_proj(hidden_states)
        else: # is cross-attention
            key_states = self.k_proj(key_value_states)
            value_states = self.v_proj(key_value_states)

        query_states = self._shape(query_states, tgt_len, bsz)
        key_states = self._shape(key_states, -1, bsz)
        value_states = self._shape(value_states, -1, bsz)

        attn_weights = self.scaled_dot_product_attention(
            query=query_states,
            key=key_states,
            value=value_states,
            mask=attention_mask,
            dropout=self.dropout,
        )
        
        if layer_head_mask is not None:
            attn_weights = layer_head_mask.view(1, -1, 1, 1) * attn_weights.view(bsz, self.num_heads, tgt_len, tgt_len)
            attn_weights = attn_weights.view(bsz * self.num_heads, tgt_len, tgt_len)

        attn_weights = attn_weights.transpose(1, 2).contiguous().view(bsz, tgt_len, self.num_heads * self.head_dim)

        attn_output = self.out_proj(attn_weights)

        return attn_output
    
__all__ = [
    "MultiheadScaledDotProductAttention",
]