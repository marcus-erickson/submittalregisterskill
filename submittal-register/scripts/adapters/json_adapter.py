"""The register as a JSON file: the lossless form, and the best one to keep between sessions."""
import register_model as model


def write(register, out, layout):
    model.dump_register(register, out)
    return len(register["items"]), sum(1 for i in register["items"] if i["needs_review"])


def read(path, layout):
    return model.load_register(path)
