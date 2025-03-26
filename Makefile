.PHONY: build run stop clean rebuild

build:
	docker-compose build

rebuild:
	docker-compose build --no-cache

run:
	xhost +local:docker
	docker-compose up

stop:
	docker-compose down

clean:
	docker-compose down --rmi all --volumes --remove-orphans
