import os.path
import sys

def assertRaisesError(test_case_instance, code, err_type, err_msg):
    """ Determine that `code` raises `err_type` with `err_msg`. """
    try:
        eval(code)
    except err_type, err:
        test_case_instance.assertEqual(str(err), err_msg)
    else:
        test_case_instance.fail("Expecting %s" % err_type)


def find_python():
    """
    Return path to python in buildout/bin. Assumes it is somewhere
    in the current directory tree.  Returns just 'python' if not found.
    """
    if sys.platform == 'win32':
        pystr = 'python.exe'
    else:
        pystr = 'python'
        
    cwd = os.getcwd()
    if cwd.endswith('buildout'):
        return os.path.join(cwd, 'bin', pystr)

    index = cwd.rfind(os.sep)
    while index > 0:
        python = os.path.join(cwd[:index], 'buildout', 'bin', pystr)
        if os.path.exists(python):
            return python
        end = index - 1
        index = cwd.rfind(os.sep, 0, end)

    return pystr

