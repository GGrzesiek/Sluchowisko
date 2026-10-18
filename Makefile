MINUTES ?= 60
PY := .venv/bin/python
LINES := 4 161 N50
API_URL ?= https://backend-6s5kkpohyq-lm.a.run.app

.PHONY: setup backend web record extract

setup:
	@test -f .env || cp .env.example .env
	@grep -qE '^ZTM_API_KEY=.+' .env || { echo "Set ZTM_API_KEY in .env to your key for the Warsaw city API (dane.um.warszawa.pl), then run make setup again."; exit 1; }
	python3 -m venv .venv
	$(PY) -m pip install -q -r requirements.txt
	$(PY) manage.py migrate
	$(PY) manage.py sync_city_data
	$(PY) manage.py build_routes $(addprefix --line ,$(LINES))
	cd web && npm ci

backend:
	$(PY) manage.py runserver

web:
	test -d web/node_modules || (cd web && npm ci)
	cd web && VITE_API_URL=$(API_URL) npm run dev

record:
	python3 -u tools/record_positions.py record --minutes $(MINUTES)

extract:
	python3 -u tools/record_positions.py extract $(REC)

.PHONY: simulate
simulate:
	python manage.py simulate_ride $(REC) $(if $(LINE),--line $(LINE)) $(if $(OUT),--out $(OUT))
