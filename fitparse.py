#!/usr/bin/env python3

import argparse
from datetime import datetime, timezone
import sys


from collections import defaultdict, namedtuple

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from garmin_fit_sdk import Decoder, Stream


DAILY_STEPS_GOAL = 10000

COMMANDS = {
    # prints all records in full multi-line format
    "dump": lambda args: dump_messages(parse_files(_get_filenames(args))),
    # prints alls steps from Monitoring
    "dump-steps": lambda args: dump_monitoring_steps(parse_files(_get_filenames(args))),
    # visualises steps history
    "steps-history": lambda args: plot_steps_history(parse_files(_get_filenames(args))),
    # visualises heart rate(pulse) history
    "pulse-history": lambda args: plot_pulse_history(parse_files(_get_filenames(args))),
    # visualises sleep history
    "sleep-history": lambda args: plot_sleep_history(parse_files(_get_filenames(args))),
}


ActivityRecord = namedtuple("ActivityRecord", ["active_calories", "distance", "steps"])


class FITMsg:

    def __init__(self, file_name, group_name, items):
        self._file_name = file_name
        self._group_name = group_name
        self._fields = dict(items)

    def __getitem__(self, key):
        return self._fields[key]

    @property
    def fields(self):
        return self._fields

    @property
    def file_name(self):
        return self._file_name

    @property
    def group_name(self):
        return self._group_name

    def has_fields(self, *args):
        return all(fld in self._fields for fld in args)

    @property
    def timestamp(self):
        return self._fields["timestamp"]


def _get_filenames(args):
    if args.batch:
        for name in sys.stdin:
            yield name.strip()
    else:
        for name in args.file_names:
            yield name


def _parse_args():
    parser = argparse.ArgumentParser(description="A program to parse FIT files")
    parser.add_argument("-b", "--batch", action='store_true', required=False,
                        help="Batch mode - will read file names from stdin if set")
    parser.add_argument("-c", "--command", required=False, default="dump",
                        choices=list(COMMANDS),
                        help="command to execute")
    parser.add_argument("file_names", nargs="+")
    return parser.parse_args()


def _read_from(file_name, decoder):
    messages, errors = decoder.read()
    for error in errors:
        print(error, file=sys.stderr)
        raise ValueError(f"failed to read: {file_name}")
    return messages


def _parse_messages(file_name, messages):
    for name, group in messages.items():
        for msg in group:
            for field_name, field_value in msg.items():
                print(f"{file_name}:{name}:{field_name}: {field_value}")
            print(f"{file_name}:{name}:---End of msg---")
        print()


def parse_file(file_name):
    stream = Stream.from_file(file_name)
    decoder = Decoder(stream)
    try:
        if not decoder.is_fit():
            raise ValueError(f"not a valid FIT file: {file_name}")
        messages = _read_from(file_name, decoder)
        for name, group in messages.items():
            for msg in group:
                yield FITMsg(file_name, name, msg.items())
    finally:
        stream.close()


def parse_files(names):
    for file_path in names:
        for msg in parse_file(file_path):
            yield msg


def dump_messages(messages):
    for msg in messages:
        for field_name, field_val in msg.fields.items():
            print(f"{msg.file_name}:{msg.group_name}:{field_name}: {field_val}")
        print(f"{msg.file_name}:{msg.group_name}:---End of msg---")


def dump_monitoring_steps(messages):
    for msg in messages:
        if msg.group_name == "monitoring_mesgs" and msg.has_fields("steps", "activity_type"):
            print(msg.file_name, msg["timestamp"], msg["activity_type"], msg["steps"])


def plot_steps_history(messages):
    ds = defaultdict(dict)
    for msg in messages:
        if msg.group_name == "monitoring_mesgs" and msg.has_fields("steps", "activity_type"):
            ts = msg.timestamp.date()
            # active_calories, distance(meters)
            # running -> (calories, distance, steps)
            # walking -> (calories, distance, steps)
            # XXX: fragile! relies on messages chronological order in files:
            #   as message timestamps contain time data not only dates
            ds[ts][msg["activity_type"]] = ActivityRecord(
                msg["active_calories"], msg["distance"], msg["steps"])
    for k in sorted(ds.keys()):
        print(k,
              "active_calories:", sum(r.active_calories for r in ds[k].values()),
              "distance:", round(sum(r.distance for r in ds[k].values()), 2),
              "steps:", sum(r.steps for r in ds[k].values()))

    dates = ds.keys()

    values = [sum(r.steps for r in ds[k].values()) for k in ds]
    distances = [round(sum(r.distance for r in ds[k].values())/1000, 2) for k in ds]
    calories = [sum(r.active_calories for r in ds[k].values()) for k in ds]

    days = len(dates)
    total = sum(values)
    avg = float(total) / days

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, sharex=True, figsize=(10, 6))

    # top: bar plot
    ax1.bar(dates, values, width=0.8, label="Steps")
    ax1.axhline(DAILY_STEPS_GOAL, color="red", linewidth=1.5, label="Daily goal")
    ax1.axhline(round(avg, 2), color="green", linewidth=1, label="Avg. steps / day")
    for x, y in zip(dates, values):
        ax1.text(x, y, str(y), ha="center", va="bottom")
    ax1.set_ylabel("Steps")
    ax1.set_title(f"Steps history over {days} day(s); total steps: {total}")
    ax1.legend()

    # bottom: separate plot sharing x-axis (simple line + markers)
    ax2.bar(dates, calories, color="tab:red", label="Active calories (line)")
    for x, y in zip(dates, calories):
        ax2.text(x, y, str(y), ha="center", va="bottom")
    ax2.set_xlabel("Date")
    ax2.set_ylabel("Active calories")
    ax2.legend()

    ax3.bar(dates, distances, color="tab:blue", label="Distance, km")
    for x, y in zip(dates, distances):
        ax3.text(x, y, str(y), ha="center", va="bottom")
    ax3.set_xlabel("Date")
    ax3.set_ylabel("Distance walked")
    ax3.legend()

    fig.autofmt_xdate()
    fig.tight_layout()
    plt.show()


def plot_pulse_history(messages):
    dates = []
    values = []
    last_ts = None
    last_ts_16 = None
    for msg in messages:
        if msg.group_name == "monitoring_mesgs":
            # HACK: handling timestamp_16 is tricky
            # this approach did not work:
            # https://forums.garmin.com/developer/fit-sdk/f/discussion/311422/fit-timestamp_16-heart-rate---excel
            # The current hack is to take previous known full timestamp
            # and then track differences between subsequent timestamp_16
            if msg.has_fields("timestamp"):
                last_ts_16 = None
                last_ts = int(msg.timestamp.timestamp())
            if msg.has_fields("timestamp_16", "heart_rate"):
                delta = 0
                real_ts = last_ts
                ts16 = msg["timestamp_16"]
                if last_ts_16 is not None and last_ts_16 < ts16:
                    delta = ts16 - last_ts_16
                    real_ts += delta

                local_ts = datetime.utcfromtimestamp(real_ts).replace(tzinfo=timezone.utc).astimezone()
                print(local_ts.strftime("%Y-%m-%dT%H:%M:%S"), msg["heart_rate"])

                dates.append(local_ts)
                values.append(msg["heart_rate"])

                last_ts_16 = ts16
                last_ts = real_ts

    plt.plot(dates, values, marker="o", color="red")
    x = plt.gca()
    x.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    x.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))

    plt.xlabel("Date")
    plt.ylabel("Heart rate")
    plt.title("Heart rate over time")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def plot_sleep_history(messages):
    started_at = None
    finished_at = None
    durations = []
    for msg in messages:
        if msg.group_name == "event_mesgs" and msg.has_fields("event_type") and msg["event_type"] == "start":
            if started_at is not None and finished_at is not None:
                print(finished_at, finished_at - started_at)
                durations.append((finished_at, finished_at - started_at))
            started_at = msg.timestamp
            print(msg.timestamp, "start")
        elif msg.group_name == "sleep_level_mesgs":
            print(msg.timestamp, "sleep")
            # if not msg.has_fields("timestamp"):
            #     print(msg.file_name)
            finished_at = msg.timestamp
    if started_at is not None and finished_at is not None:
        print(finished_at, finished_at - started_at)
        durations.append((finished_at, finished_at - started_at))

    dates = [d[0].date() for d in durations]
    values = [round(d[1].seconds / 3600., 2) for d in durations]
    plt.bar(dates, values, width=0.8, color="blue")
    for x, y in zip(dates, values):
        plt.text(x, y, str(y), ha="center", va="bottom")

    plt.xlabel("Date")
    plt.ylabel("Sleep duration, hours")
    plt.title(f"Sleep duration over time from {dates[0]} to {dates[-1]}")
    plt.grid(True)
    plt.tight_layout()
    plt.show()
    plt.show()


def main(args):
    COMMANDS[args.command](args)


if __name__ == "__main__":
    main(_parse_args())
