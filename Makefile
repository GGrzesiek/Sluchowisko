MINUTES ?= 60

.PHONY: record extract

record:
	python3 -u tools/record_positions.py record --minutes $(MINUTES)

extract:
	python3 -u tools/record_positions.py extract $(REC)
