import click
from code42cli.extensions import script, sdk_options

@click.command()
@sdk_options
def my_command(state):
    user = state.sdk.users.get_current()
    print(user["username"], user["userId"])

if __name__ == "__main__":
    script.add_command(my_command)
    script()
