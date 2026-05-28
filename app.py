from flask import Flask, render_template, request

app = Flask(__name__)
TASK_COUNT = 10
TASK_LABELS = [f"T{i + 1}" for i in range(TASK_COUNT)]


def parse_precedence(raw_precedence):
    predecessors = []
    for i, raw in enumerate(raw_precedence):
        parsed = []
        if raw:
            for token in raw.replace(";", ",").split(","):
                token = token.strip()
                if token:
                    if not token.isdigit():
                        raise ValueError(f"Precedencia inválida en {TASK_LABELS[i]}: '{token}'")
                    index = int(token) - 1
                    if index < 0 or index >= TASK_COUNT:
                        raise ValueError(f"Precedencia fuera de rango en {TASK_LABELS[i]}: '{token}'")
                    if index == i:
                        raise ValueError(f"{TASK_LABELS[i]} no puede preceder a sí misma.")
                    parsed.append(index)
        predecessors.append(parsed)
    return predecessors


def compute_successors(predecessors):
    successors = [[] for _ in range(TASK_COUNT)]
    for task, preds in enumerate(predecessors):
        for pred in preds:
            successors[pred].append(task)
    return successors


def compute_rpw(times, successors):
    memo = {}
    visit_state = [0] * TASK_COUNT

    def dfs(task):
        if visit_state[task] == 1:
            raise ValueError("Ciclo detectado en las precedencias. Verifique las relaciones ingresadas.")
        if visit_state[task] == 2:
            return memo[task]
        visit_state[task] = 1
        weight = times[task]
        if successors[task]:
            weight += max(dfs(succ) for succ in successors[task])
        memo[task] = weight
        visit_state[task] = 2
        return weight

    for task in range(TASK_COUNT):
        if visit_state[task] == 0:
            dfs(task)
    return [memo[i] for i in range(TASK_COUNT)]


def schedule_rpw(times, predecessors, cycle_time):
    successors = compute_successors(predecessors)
    rpw_values = compute_rpw(times, successors)
    unscheduled = set(range(TASK_COUNT))
    assigned_station = {}
    station_tasks = []

    while unscheduled:
        available = [t for t in unscheduled if all(pred in assigned_station for pred in predecessors[t])]
        if not available:
            raise ValueError("No hay tareas disponibles para asignar. Verifique las precedencias ingresadas.")
        available.sort(key=lambda t: (-rpw_values[t], t))
        remaining = cycle_time
        station = []
        for task in available:
            if times[task] <= remaining:
                station.append(task)
                remaining -= times[task]
        if not station:
            min_time = min(times[t] for t in available)
            raise ValueError(f"El tiempo de ciclo es demasiado bajo. La menor tarea disponible requiere {min_time} horas.")
        for task in station:
            assigned_station[task] = len(station_tasks) + 1
            unscheduled.remove(task)
        station_tasks.append(station)

    total_idle = len(station_tasks) * cycle_time - sum(times)
    return station_tasks, rpw_values, total_idle


@app.route("/", methods=["GET", "POST"])
def balanceo():
    error = None
    result = None
    if request.method == "POST":
        try:
            raw_cycle_time = request.form.get("cycle_time", "").strip()
            if raw_cycle_time == "":
                raise ValueError("Debe ingresar un tiempo de ciclo deseado.")
            cycle_time = int(raw_cycle_time)
            if cycle_time <= 0:
                raise ValueError("El tiempo de ciclo debe ser un número entero positivo.")

            times = []
            raw_precedence = []
            for i in range(TASK_COUNT):
                raw_time = request.form.get(f"time_{i}", "").strip()
                if raw_time == "":
                    raise ValueError(f"Falta el tiempo para la tarea {TASK_LABELS[i]}.")
                task_time = int(raw_time)
                if task_time <= 0:
                    raise ValueError(f"El tiempo de {TASK_LABELS[i]} debe ser un entero positivo.")
                times.append(task_time)
                raw_precedence.append(request.form.get(f"pred_{i}", "").strip())

            predecessors = parse_precedence(raw_precedence)
            station_tasks, rpw_values, total_idle = schedule_rpw(times, predecessors, cycle_time)
            task_details = [
                {
                    "label": TASK_LABELS[i],
                    "time": times[i],
                    "rpw": rpw_values[i],
                    "predecessors": ", ".join(TASK_LABELS[p] for p in predecessors[i]) or "—",
                }
                for i in range(TASK_COUNT)
            ]
            result = {
                "cycle_time": cycle_time,
                "station_tasks": [[TASK_LABELS[t] for t in station] for station in station_tasks],
                "task_details": task_details,
                "total_time": sum(times),
                "total_idle": total_idle,
                "stations": len(station_tasks),
            }
        except ValueError as exc:
            error = str(exc)

    return render_template(
        "balanceo.html",
        task_labels=TASK_LABELS,
        error=error,
        result=result,
        request_form=request.form if request.method == "POST" else {},
    )