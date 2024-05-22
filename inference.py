from tokenizers import Tokenizer
from .prepare_dataset import read_tokenizer
from .model import GET_MODEL
import torch
from .utils import weights_file_path
from .custom_models_bart import load_model
from .beam_search import beam_search

def prepare_inference(config):
    device = config["device"]

    # read tokenizer
    tokenizer_src, tokenizer_tgt = read_tokenizer(config=config)
    
    # get model
    model_train = config["model_train"] 
    get_model = GET_MODEL[model_train]
    model = get_model(
        config=config,
        tokenizer_src=tokenizer_src,
        tokenizer_tgt=tokenizer_tgt,
    ).to(device)

    # get model_filename
    model_filename = weights_file_path(config)[-1]

    model = load_model(
        checkpoint=model_filename,
        model=model
    )

    return config, model, tokenizer_src, tokenizer_tgt

def inference(src, beam_size, prepare_inference):
    config, model, tokenizer_src, tokenizer_tgt = prepare_inference

    with torch.no_grad():
        model.eval()
    
        model_out = beam_search(
            model=model,
            config=config,
            beam_size=beam_size,
            tokenizer_src=tokenizer_src,
            tokenizer_tgt=tokenizer_tgt,
            src=src,
        )

        pred = tokenizer_tgt.decode(model_out.detach().cpu().numpy())

        return pred
    
def pipeline(config, src, beam_size):
    print("SOURCE:")
    print(src)
    print("PREDICT:")
    print(inference(
        src=src,
        beam_size=beam_size,
        prepare_inference=prepare_inference(config),
    ))

__all__ = ["prepare_inference", "inference", "pipeline"]