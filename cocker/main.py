# %%
# %cd ~/codes/idea/cocker/cocker
# %ls

# %%

from conda_merge import *
from ruamel import yaml
import subprocess
from pathlib import Path

from absl import app, flags, logging


# %%


ENV = dict


def merge_envs(env_definitions: list[ENV], remove_builds=True) -> ENV:
    """Main script entry point.

    `args` is a Namescpace object, `args.files` should be a list of file paths
    to merge.
    No return value, the unified yaml file is printed to stdout.
    If an error occurs, a message is printed to stderr and exception is raised.

    """
    # env_definitions = [read_file(f) for f in args.files]
    unified_definition = {}
    name = merge_names(env.get("name") for env in env_definitions)
    if name:
        unified_definition["name"] = name
    try:
        channels = merge_channels(env.get("channels") for env in env_definitions)
    except MergeError as exc:
        print(
            "Falied to merge channel priorities.\n{}\n".format(exc.args[0]),
            file=sys.stderr,
        )
        raise
    if channels:
        unified_definition["channels"] = channels
    deps = merge_dependencies(
        [env.get("dependencies") for env in env_definitions],
        remove_builds=remove_builds,
    )
    if deps:
        unified_definition["dependencies"] = deps
    # dump the unified environment definition to stdout
    # return yaml.dump(unified_definition, indent=2, default_flow_style=False)
    return unified_definition


def pretty_dump(env_definition: ENV, stream):
    yml = yaml.YAML()
    yml.indent(sequence=4, offset=2)
    yml.dump(env_definition, stream)


def parse_cocker(
    input_file: Path, output_file: Path = Path("environment.yml"), dry_run: bool = False
):
    with open(input_file, "r") as f:
        data = yaml.load(f, yaml.RoundTripLoader)

    try:
        env_path = Path(__file__).parent / "environments"
    except Exception as e:
        env_path = Path().parent / "environments"

    CONDA_ENVS = [f.stem for f in env_path.glob("*")]
    logging.debug(f"CONDA_ENVS: {CONDA_ENVS}")
    merge_yamls = []
    yamls: list[str] = data.pop("includes", ["base"])
    for yaml_file in yamls:
        if yaml_file.endswith(".yaml") or yaml_file.endswith(".yml"):
            assert Path(yaml_file).exists(), f"File not found: {yaml_file}"
            merge_yamls.append(yaml_file)
        elif yaml_file.startswith("http") or yaml_file.startswith("https"):
            # TODO
            pass
        else:
            assert yaml_file in CONDA_ENVS, (
                f"Conda env not found: {yaml_file}"
                f"Predefined envs including: {CONDA_ENVS}"
            )
            merge_yamls.append(env_path / f"{yaml_file}.yml")

    # cmds = ["conda-merge"] + [str(y) for y in merge_yamls]
    # logging.debug(cmds)

    # if merged_yaml.exists():
    #     if input(f"Will overwrite {merged_yaml}, continue? Y/n").lower() in ["n", "no"]:
    #         exit
    # process = subprocess.Popen(cmds, stdout=subprocess.PIPE)
    # if not dry_run:
    #     stdout, stderr = process.communicate()

    #     yml = yaml.YAML()
    #     yml.indent(sequence=4, offset=2)
    #     with open(output_file, "w") as file:
    #         yml.dump(yaml.safe_load(stdout), file)
    env_definitions = [read_file(f) for f in merge_yamls]
    env_definitions.append(data)
    env_definition = merge_envs(env_definitions)
    stream = open(output_file, "w") if not dry_run else sys.stdout
    return pretty_dump(env_definition, stream)


# %%

# parse_cocker(Path("../cocker-dev.yml"), Path("environment.yml"), dry_run=False)

# %%


FLAGS = flags.FLAGS

# flags.DEFINE_string("param1", None, "Parameter 1 description")
# flags.DEFINE_multi_string("pip", None, "pip requiremnets")
# flags.DEFINE_multi_string(
#     "scripts", None, "execuable scripts to be execued after pip install"
# )
flags.DEFINE_bool("dryrun", False, "dry run", short_name="d")
flags.DEFINE_string("name", "cocker", "name of conda environment", short_name="n")
flags.DEFINE_string(
    "output_file", "environment.yml", "name of conda environment", short_name="o"
)


def main(argv):
    include_files = argv[1:]
    assert len(include_files) == 1, "Only accept one file now"
    parse_cocker(Path(include_files[0]), Path(FLAGS.output_file), dry_run=FLAGS.dryrun)


def absl_main():
    app.run(main)


if __name__ == "__main__":
    absl_main()
