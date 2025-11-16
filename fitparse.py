#!/usr/bin/env python3

import argparse
from datetime import datetime, timezone
import sys


from collections import defaultdict, namedtuple

import numpy as np
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from garmin_fit_sdk import Decoder, Stream


DAILY_STEPS_GOAL = 10000
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

_cmd = namedtuple("CLICommand", ["cmd", "description"])

COMMANDS = {}


def cli_command(name, description=""):
    def _dec(f):
        COMMANDS[name] = _cmd(f, description)
        return f
    return _dec


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
        if self.group_name == "stress_level_mesgs":
            return self._fields.get("stress_level_time")
        return self._fields.get("timestamp")

    def timestamp_in(self, since=None, until=None):
        if not self.timestamp:
            return True
        if since is not None and self.timestamp.date() < since.date():
            return False
        if until is not None and self.timestamp.date() > until.date():
            return False

        return True


def _get_filenames(args):
    if args.batch:
        for name in sys.stdin:
            yield name.strip()
    else:
        for name in args.file_names:
            yield name


def _parse_time_interval(s):
    try:
        s = s.strip()
        val = datetime.strptime(s, "%Y-%m-%d")
        return val.replace(tzinfo=datetime.now().astimezone().tzinfo)
    except Exception as ex:
        raise argparse.ArgumentTypeError(f"Bad time interval: {ex}")


def _parse_args():
    parser = argparse.ArgumentParser(description="A program to parse FIT files")
    parser.add_argument("-b", "--batch", action='store_true', required=False,
                        help="Batch mode - will read file names from stdin if set")
    parser.add_argument("-c", "--command", required=False, default="dump",
                        choices=list(COMMANDS),
                        help="Command to execute")
    parser.add_argument("-f", "--fields", type=str, required=False, default="",
                        help="Fields to dump in csv mode")
    parser.add_argument("-s", "--since", default=None, required=False,
                        type=_parse_time_interval,
                        help="show timeseries data on or newer than the specified date")
    parser.add_argument("-p", "--plot", action="store_true", required=False,
                        help="Plot data if sub-command supports it.")
    parser.add_argument("-u", "--until", default=None, required=False,
                        type=_parse_time_interval,
                        help="show timeseries data on or older than the specified date")
    parser.add_argument("file_names", nargs="*")
    return parser.parse_args()


def _read_from(file_name, decoder):
    messages, errors = decoder.read()
    for error in errors:
        print(error, file=sys.stderr)
        raise ValueError(f"failed to read: {file_name}")
    return messages


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


def parse_files(args):
    for file_path in _get_filenames(args):
        for msg in parse_file(file_path):
            if not msg.timestamp_in(args.since, args.until):
                continue
            yield msg


def print_table(table, dt_format="%Y-%m-%d"):
    for row in table:
        row_str = list(row)
        row_str[0] = row[0].strftime(dt_format)
        print(" ".join([str(v) for v in row_str]))


# pylint: disable=R0913
def bar_plot(p, dates, values,
             title="", color=None, plot_label="", x_label="", y_label=""):
    p.bar(dates, values, width=0.8, label=plot_label, color=color)
    for x, y in zip(dates, values):
        p.text(x, y, str(y), ha="center", va="bottom")
    try:
        p.set_xlabel(x_label)
    except AttributeError:
        p.xlabel(x_label)
    try:
        p.set_ylabel(y_label)
    except AttributeError:
        p.ylabel(y_label)
    try:
        p.set_title(title)
    except AttributeError:
        p.title(title)


def plot_hourly_data_with_lines(
    dates,
    values,
    label="",
    title="",
    color="red",
    x_label="Time",
    y_label="",
    y_locator=None,
):
    try:
        if np.size(dates) < 1:
            return
    except:
        if not dates or not values:
            return

    plt.plot(dates, values, marker="o", color=color, label=label)
    ax = plt.gca()
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
    if y_locator is not None:
        ax.yaxis.set_major_locator(y_locator)
    ax.tick_params(axis='x', rotation=45)
    ax.legend()

    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(title)

    plt.grid(True)
    plt.tight_layout()
    plt.show()


@cli_command("csv", description="prints records in csv format")
def dump_csv(args):
    for msg in parse_files(args):
        fields = []
        if args.fields:
            fields = sorted(args.fields.split(","))
        vals = [msg.file_name, msg.group_name, msg.timestamp or "?"]
        vals.extend(msg.fields.get(f.lower(), "?") for f in fields)
        print(",".join([str(v) for v in vals]))


@cli_command("dump", description="prints all records in full multi-line format")
def dump_messages(args):
    for msg in parse_files(args):
        for field_name, field_val in msg.fields.items():
            print(f"{msg.file_name}:{msg.group_name}:{field_name}: {field_val}")
        print(f"{msg.file_name}:{msg.group_name}:---End of msg---")


@cli_command("dump-steps", description="prints alls steps from Monitoring")
def dump_monitoring_steps(args):
    for msg in parse_files(args):
        if msg.group_name == "monitoring_mesgs" and msg.has_fields("steps", "activity_type"):
            print(msg.file_name, msg["timestamp"], msg["activity_type"], msg["steps"])


@cli_command("steps", description="visualises steps history")
def plot_steps_history(args):
    # pylint: disable=too-many-locals
    ds = defaultdict(dict)
    for msg in parse_files(args):
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

    if not ds:
        return
    if not args.plot:
        return

    dates = ds.keys()

    values = [sum(r.steps for r in ds[k].values()) for k in ds]
    distances = [round(sum(r.distance for r in ds[k].values())/1000, 2) for k in ds]
    calories = [sum(r.active_calories for r in ds[k].values()) for k in ds]

    days = len(dates)
    total = sum(values)
    avg = float(total) / days

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, sharex=True, figsize=(10, 6))

    # steps plot
    bar_plot(ax1, dates, values, plot_label="Steps", x_label="Date", y_label="Steps",
             title=f"Steps history over {days} day(s); total steps: {total}")
    ax1.axhline(DAILY_STEPS_GOAL, color="red", linewidth=1.5, label="Daily goal")
    ax1.axhline(round(avg, 2), color="green", linewidth=1, label="Avg. steps / day")
    ax1.legend()

    # calories plot
    bar_plot(ax2, dates, calories, color="tab:red", plot_label="Active calories (line)",
             x_label="Date", y_label="Active calories")
    ax2.legend()

    # distance plot
    bar_plot(ax3, dates, distances, color="tab:blue", plot_label="Distance, km",
             x_label="Date", y_label="Kilometers")
    ax3.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax3.legend()

    fig.autofmt_xdate()
    fig.tight_layout()
    plt.show()


@cli_command("pulse", description="visualises heart rate(pulse) history")
def plot_pulse_history(args):
    rows = []
    last_ts = None
    last_ts_16 = None

    # HACK: since / until filters do not work in parse_files
    #   as we manually calculate timestamps below. Hence apply since / until filters
    #   manually here to the calculated timestamps.
    since, until = args.since, args.until
    args.since, args.until = None, None
    for msg in parse_files(args):
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

                last_ts_16 = ts16
                last_ts = real_ts

                # convert real_ts to the instant expressed in the local timezone.
                local_ts = datetime.utcfromtimestamp(real_ts).replace(tzinfo=timezone.utc).astimezone()

                if since is not None and local_ts.date() < since.date():
                    continue
                if until is not None and local_ts.date() > until.date():
                    continue

                rows.append([local_ts, msg["heart_rate"]])

    table = np.array(rows)
    print_table(table, dt_format=DATETIME_FORMAT)
    if not args.plot:
        return
    plot_hourly_data_with_lines(table[:, 0], table[:, 1],
                                label="Pulse",
                                title="Heart rate over time",
                                y_label="Heart rate")


@cli_command("sleep", description="visualises sleep history")
def plot_sleep_history(args):
    # pylint: disable=R0914
    rows = []
    row = [0] * 3
    started_at, finished_at = None, None
    for msg in parse_files(args):
        if msg.group_name == "event_mesgs":
            if msg.fields.get("event_type") == "start":
                started_at = msg.timestamp
            elif msg.fields.get("event_type") == "stop":
                if started_at is None:
                    continue
                finished_at = msg.timestamp
                duration = round((finished_at - started_at).seconds / 3600., 2)
                row[0], row[1] = finished_at.date(), duration
                rows.append(row)
                row = [0] * 3
        elif msg.group_name == "sleep_assessment_mesgs":
            # XXX: sleep_assessment_mesgs has no timestamp
            # Relying on the fact that it goes right after
            # event_mesgs.event_type = stop
            if finished_at is not None and rows:
                rows[-1][2] = msg["overall_sleep_score"]

    table = np.array(rows)
    print_table(table)

    if not rows:
        return
    if not args.plot:
        return

    ax1 = plt.gca()
    bar_plot(ax1, table[:, 0], table[:, 1],
             plot_label="Sleep duration",
             color="blue", x_label="Date", y_label="Hours",
             title=f"Sleep duration over time from {table[0, 0]} to {table[-1, 0]}")

    ax1.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))

    ax2 = ax1.twinx()
    ax2.plot(table[:, 0], table[:, 2], marker="o", color="red", label="Sleep score")
    ax2.set_ylim(0, None)

    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(handles1 + handles2, labels1 + labels2)

    plt.grid(True)
    plt.tight_layout()
    plt.show()


@cli_command("stress", description="visualises stress history")
def plot_stress_history(args):
    rows = []
    for msg in parse_files(args):
        if msg.group_name == "stress_level_mesgs":
            dt_val = msg.timestamp.astimezone()
            val = msg["stress_level_value"]
            if val < 0:
                continue
            rows.append([dt_val, val])

    table = np.array(rows)
    print_table(table, dt_format=DATETIME_FORMAT)
    if not args.plot:
        return
    plot_hourly_data_with_lines(table[:, 0], table[:, 1],
                                label="Stress level",
                                title="Stress level over time",
                                y_label="Stress level [0-100]",
                                y_locator=mticker.MultipleLocator(10))


def main(args):
    try:
        COMMANDS[args.command].cmd(args)
    except (KeyboardInterrupt, BrokenPipeError):
        pass


if __name__ == "__main__":
    main(_parse_args())
