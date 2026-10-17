MINUTES ?= 60

.PHONY: record extract

record:
	python3 -u tools/record_positions.py record --minutes $(MINUTES)

extract:
	python3 -u tools/record_positions.py extract $(REC)

.PHONY: simulate
simulate:
	python manage.py simulate_ride $(REC) $(if $(LINE),--line $(LINE)) $(if $(OUT),--out $(OUT))
