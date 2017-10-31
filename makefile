create_pyenv = "pipenv --python 3.6"
install_dev_packages = "pipenv install --dev"
build_proj = "pipenv run python scripts/build.py"
publish_proj = "pipenv run python scripts/publish.py"

init:
	$(info [INIT PROJECT])
	"$(create_pyenv)"
	"$(install_dev_packages)"


build:
	$(info [BUILD])
	"$(build_proj)"

publish:
	$(info [PUBLISH])
	"$(publish_proj)"

