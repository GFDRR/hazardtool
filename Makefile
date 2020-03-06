
AUTHUSERFILE ?= /var/www/vhosts/wb-thinkhazard/conf/.htpasswd
DATA ?= world

-include local.mk

export INI_FILE ?= c2c://development.ini

export PGHOST ?= db
export PGHOST_SLAVE ?= db
export PGPORT ?= 5432

export PGDATABASE_PUBLIC ?= thinkhazard
export PGUSER_PUBLIC ?= thinkhazard
export PGPASSWORD_PUBLIC ?= thinkhazard

export PGDATABASE_ADMIN ?= thinkhazard_admin
export PGUSER_ADMIN ?= thinkhazard
export PGPASSWORD_ADMIN ?= thinkhazard


.PHONY: help_old
help_old:
	@echo "Usage: make <target>"
	@echo
	@echo "Possible targets:"
	@echo
	@echo "- install                 Install thinkhazard"
	@echo "- buildcss                Build CSS"
	@echo "- check                   Check the code with flake8, jshint and bootlint"
	@echo "- test                    Run the unit tests"
	@echo "- dist                    Build a source distribution"
	@echo "- routes                  Show the application routes"
	@echo "- watch                   Run the build target when files in static dir change"
	@echo "- extract_messages        Extract translation string and update the .pot file"
	@echo "- transifex-push          Push translations to transifex"
	@echo "- transifex-pull          Pull translations from transifex"
	@echo "- transifex-import        Import po files into database"
	@echo "- compile_catalog         Compile language files"
	@echo

default: help

.PHONY: help
help: ## Display this help message
	@echo "Usage: make <target>"
	@echo
	@echo "Possible targets:"
	@grep -Eh '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "    %-20s%s\n", $$1, $$2}'


################
# Entry points #
################

DOCKER_CMD=docker-compose -f docker-compose-test.yaml run --rm --user `id -u` test

DOCKER_MAKE_CMD=$(DOCKER_CMD) make -f docker.mk

.PHONY: build
build: ## Build docker images
build: docker_build_thinkhazard docker_build_builder docker_build_testdb

.PHONY: bash
bash: ## Open bash in builder
	$(DOCKER_CMD) bash

.PHONY: check
check: ## Check the code with flake8, jshint and bootlint
check:
	$(DOCKER_MAKE_CMD) check

.PHONY: buildcss
buildcss: ## Build css files
buildcss:
	$(DOCKER_MAKE_CMD) buildcss

.PHONY: compile_catalog
compile_catalog: ## Compile language files
compile_catalog:
	$(DOCKER_MAKE_CMD) compile_catalog

.PHONY: test
test: ## Run automated tests
	docker-compose -f docker-compose-test.yaml run --rm test nosetests -v


.PHONY: clean
clean:
	rm -rf thinkhazard/static/build
	rm -rf thinkhazard/static/fonts
	rm -rf `find thinkhazard/locale -name *.po 2> /dev/null`
	rm -rf `find thinkhazard/locale -name *.mo 2> /dev/null`
	docker-compose down -v --remove-orphans

.PHONY: cleanall
cleanall: clean
	docker rmi -f \
		camptocamp/thinkhazard \
		camptocamp/thinkhazard-builder

.PHONY: .env
.env:
	rm -f .env
	cat .env.tmpl | envsubst > .env

#######################
# Build docker images #
#######################

.PHONY: docker_build_thinkhazard
docker_build_thinkhazard:
	docker build \
		--build-arg TX_USR=${TX_USR} \
		--build-arg TX_PWD=${TX_PWD} \
		--target app -t camptocamp/thinkhazard .

.PHONY: docker_build_builder
docker_build_builder:
	docker build \
		--build-arg TX_USR=${TX_USR} \
		--build-arg TX_PWD=${TX_PWD} \
		--target builder -t camptocamp/thinkhazard-builder .

.PHONY: docker_build_testdb
docker_build_testdb:
	docker build -t camptocamp/thinkhazard-testdb docker/testdb


##############
# Processing #
##############

.PHONY: harvest
harvest: ## Harvest GeoNode layers metadata
	docker-compose run --rm thinkhazard harvest -v

.PHONY: download
download: ## Download raster data from GeoNode
	.build/venv/bin/download -v

.PHONY: complete
complete: ## Mark complete hazardsets as such
	.build/venv/bin/complete -v

.PHONY: process
process: ## Compute hazard levels from hazardsets for administrative divisions level 2
	.build/venv/bin/process -v

.PHONY: decisiontree
decisiontree: ## Run the decision tree and perform upscaling
	.build/venv/bin/decision_tree -v

.PHONY: publish
publish: ## Publish validated data on public web site
	.build/venv/bin/publish $(INI_FILE)


#######################
# Initialize database #
#######################

.PHONY: populatedb
populatedb: ## Populates database. Use DATA=turkey if you want to work with a sample data set
populatedb: initdb import_admindivs import_recommendations import_contacts

.PHONY: initdb
initdb: ## Initialize database model
	docker-compose run --rm thinkhazard initialize_thinkhazard_db "$(INI_FILE)#admin"

.PHONY: initdb_force
initdb_force:
	docker-compose run --rm thinkhazard initialize_thinkhazard_db "$(INI_FILE)#admin" --force=1

.PHONY: reinit_all
reinit_all: ## Completely clear and re-init database. Only for developement purpose
reinit_all: initdb_force import_admindivs import_recommendations import_contacts harvest download complete process decisiontree

.PHONY: import_admindivs
import_admindivs: ## Import administrative divisions. Use DATA=turkey or DATA=indonesia if you want to work with a sample data set
import_admindivs: \
		/tmp/thinkhazard/admindiv/$(DATA)/g2015_2014_0_upd270117.shp \
		/tmp/thinkhazard/admindiv/$(DATA)/g2015_2014_1_upd270117.shp \
		/tmp/thinkhazard/admindiv/$(DATA)/g2015_2014_2_upd270117.shp
	@while [ -z "$$CONTINUE" ]; do \
		read -r -p "This will remove all the existing data in the administrative divisions table. Continue? [y] " CONTINUE;  \
	done ; \
	[ $$CONTINUE = "y" ] || [ $$CONTINUE = "Y" ] || (echo "Exiting."; exit 1;)
	.build/venv/bin/import_admindivs $(INI_FILE) folder=/tmp/thinkhazard/admindiv/$(DATA)

/tmp/thinkhazard/admindiv/$(DATA)/%.shp: /tmp/thinkhazard/admindiv/$(DATA)/%.zip
	unzip -o $< -d /tmp/thinkhazard/admindiv/$(DATA)

/tmp/thinkhazard/admindiv/$(DATA)/%_upd270117.zip:
	mkdir -p $(dir $@)
	wget -nc "http://dev.camptocamp.com/files/thinkhazard/$(DATA)/$(notdir $@)" -O $@

.PHONY: import_recommendations
import_recommendations: ## Import recommendations
	docker-compose run --rm thinkhazard import_recommendations "$(INI_FILE)#admin"

.PHONY: import_contacts
import_contacts: .build/requirements.timestamp
	docker-compose run --rm thinkhazard import_contacts "$(INI_FILE)#admin"


.PHONY: transifex-import
transifex-import: .build/requirements.timestamp
	.build/venv/bin/importpo $(INI_FILE)

.PHONY: routes
routes:
	.build/venv/bin/proutes $(INI_FILE)


.PHONY: dbtunnel
dbtunnel:
	@echo "Opening tunnel…"
	ssh -N -L 9999:localhost:5432 wb-thinkhazard-dev-1.sig.cloud.camptocamp.net


.PHONY: watch
watch: .build/dev-requirements.timestamp
	@echo "Watching static files..."
	.build/venv/bin/nosier -p thinkhazard/static "make buildcss"



.PHONY: extract_messages
extract_messages:
	.build/venv/bin/pot-create -c lingua.cfg -o thinkhazard/locale/thinkhazard.pot thinkhazard/templates thinkhazard/dont_remove_me.enum-i18n
	.build/venv/bin/pot-create -c lingua.cfg -o thinkhazard/locale/thinkhazard-database.pot thinkhazard/dont_remove_me.db-i18n
	# removes the creation date to avoid unnecessary git changes
	sed -i '/^"POT-Creation-Date: /d' thinkhazard/locale/thinkhazard.pot

.PHONY: transifex-push
transifex-push: $(HOME)/.transifexrc
	.build/venv/bin/tx push -s


