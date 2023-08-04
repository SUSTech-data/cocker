from conda_merge import *
from ruamel import yaml
from pathlib import Path

from absl import app, flags, logging
import os
import sys


# %%


Environment = dict


def merge_envs(env_definitions: list[Environment], remove_builds=True) -> Environment:
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


def pretty_dump(env_definition: Environment, stream):
    yml = yaml.YAML()
    yml.indent(sequence=4, offset=2)
    yml.dump(env_definition, stream)


try:
    ENV_PATH = Path(__file__).parent / "environments"
except Exception as e:
    ENV_PATH = Path().parent / "environments"

USER_ENV_PATH = Path(os.getenv("XDG_CONFIG_HOME", None) or Path.home()) / ".cocker"

CONDA_ENVS = {f.stem: f for f in ENV_PATH.glob("*.yml")}
CONDA_ENVS.update({f.stem: f for f in USER_ENV_PATH.glob("*.yml")})


def read_yml(yaml_file: str) -> Environment:
    if yaml_file.endswith(".yaml") or yaml_file.endswith(".yml"):
        assert Path(yaml_file).exists(), f"File not found: {yaml_file}"
        logging.info(f"Merge env {yaml_file}")
        return read_file(yaml_file)
    elif yaml_file.startswith("http") or yaml_file.startswith("https"):
        # TODO
        raise NotImplementedError
    else:
        assert yaml_file in CONDA_ENVS, (
            f"Conda env not found: {yaml_file}"
            f"Predefined envs including: {CONDA_ENVS}"
        )
        # merge_yamls.append(ENV_PATH / f"{yaml_file}.yml")
        logging.info(f"Merge env {yaml_file} from predefined envs")

        return read_file(ENV_PATH / f"{yaml_file}.yml")


def get_environments(data: Environment) -> list[Environment]:
    yamls: list[str] = data.pop("includes", [])
    env_definitions = [data]
    for yaml_file in yamls:
        data = read_yml(yaml_file)
        env_definitions.extend(get_environments(data))
    return env_definitions


def parse_cocker(
    input_file: str, output_file: Path = Path("environment.yml"), dry_run: bool = False
):
    data = read_yml(input_file)

    env_definitions = get_environments(data)
    env_definition = merge_envs(env_definitions)
    stream = open(output_file, "w") if not dry_run else sys.stdout
    return pretty_dump(env_definition, stream)


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
    logging.debug(f"argv: {argv}")
    logging.debug(USER_ENV_PATH)
    logging.debug(ENV_PATH)
    logging.debug(f"CONDA_ENVS: {CONDA_ENVS}")
    include_files = argv[1:]
    assert len(include_files) == 1, "Only accept one file now"
    parse_cocker(include_files[0], Path(FLAGS.output_file), dry_run=FLAGS.dryrun)


def absl_main():
    app.run(main)


if __name__ == "__main__":
    absl_main()
