
import vhpi.state as state


def exit(code, msg=None, level=None):
    kill_processes()
    state.job.alive = False
    log.job_out(code, self.init_time)
