# import the tiralib library
from tiralib.tiramisu import TiramisuProgram, Schedule, tiramisu_actions
from tiralib.config.config import BaseConfig

# initialize the TiraLib configuration
BaseConfig.init()

# Load the Tiramisu Program from the file and create a TiraLibCPP server
# IMPORTANT! This needs a working path to the TiraLibCPP library set in the config file of TiraLib
tiramisu_program = TiramisuProgram.init_server(
    "./examples/function_blur_MINI_generator.cpp",
    from_file=True,
    load_annotations=True,
    load_tree=True,
    reuseServer=True,
)

# The rest of the code is the same as in using TiraLib alone

# Create a schedule object
schedule = Schedule(tiramisu_program)

# Apply the optimizations to the schedule
schedule.add_optimizations([tiramisu_actions.Parallelization([("comp_blur", 0)])])

# execute the schedule and get the execution times
execution_times = schedule.execute()

print(execution_times)
