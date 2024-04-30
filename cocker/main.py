from conda_merge import *
from ruamel import yaml
from pathlib import Path
import itertools

from absl import app, flags, logging
import os
import sys
from tqdm.auto import tqdm


# %%


Environment = dict


def _remove_build(dep):
    """Remove build version if exists, return dep"""
    m = re.match(r"([^=]+=[^=]+)=([^=]+)$", dep, re.IGNORECASE)
    return m.group(1) if m else dep


def merge_dependencies(deps_list, remove_builds=False):
    """Merge all dependencies to one list and return it.

    Two overlapping dependencies (e.g. package-a and package-a=1.0.0) are not
    unified, and both are left in the list (except cases of exactly the same
    dependency). Conda itself handles that very well so no need to do this ourselves,
    unless you want to prettify the output by hand.

    """
    only_pips = []
    unified_deps = []
    for deps in deps_list:
        if deps is None:  # not found in this environment definition
            continue
        for dep in deps:
            if isinstance(dep, dict) and dep["pip"]:
                only_pips.append(dep["pip"])
            else:
                if remove_builds:
                    dep = _remove_build(dep)
                if dep not in unified_deps:
                    unified_deps.append(dep)
    unified_deps = sorted(unified_deps)
    if only_pips:
        unified_deps.append(merge_pips(only_pips))
    return unified_deps


def merge_pips(pip_list):
    """Merge pip requirements lists the same way as `merge_dependencies` work"""
    # return {"pip": ({req for reqs in pip_list for req in reqs})}
    all_pip = list(itertools.chain(*pip_list))
    # return {"pip": pd.Series(all_pip).drop_duplicates().tolist()}
    return {"pip": list(dict.fromkeys(all_pip))}


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


def get_environments(data: Environment | list) -> list[Environment]:
    # match data:
    if isinstance(data, dict):
        yamls: list[str] = data.pop("includes", [])
        env_definitions = [data]
    if isinstance(data, list):
        yamls = data
        env_definitions = []
    if isinstance(data, str):
        yamls = [data]
        env_definitions = []
    for yaml_file in yamls:
        data = read_yml(yaml_file)
        env_definitions.extend(get_environments(data))
    return env_definitions


def parse_cocker(
    input_files: str | list[str],
    output_file: Path = Path("environment.yml"),
    dry_run: bool = False,
):
    # data = read_yml(input_file)

    env_definitions = get_environments(input_files)
    env_definition = merge_envs(env_definitions)
    stream = open(output_file, "w") if not dry_run else sys.stdout
    deps_wt_pips = []
    pip_deps = None
    for dep in env_definition.get("dependencies", []):
        if isinstance(dep, dict) and "pip" in dep:
            pip_deps = dep["pip"]
        else:
            deps_wt_pips.append(dep)
    env_definition["dependencies"] = deps_wt_pips
    if pip_deps:
        open(Path(output_file).parent / "requirements.txt", "w").write(
            "\n".join(pip_deps)
        )

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
    logging.debug(f"{argv=}")
    include_files = argv[1:]
    logging.debug(f"{include_files=}")
    assert len(include_files) >= 1, "Environment file is required."
    parse_cocker(include_files, Path(FLAGS.output_file), dry_run=FLAGS.dryrun)


def absl_main():
    app.run(main)


if __name__ == "__main__":
    absl_main()
