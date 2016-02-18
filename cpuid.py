# -*- coding: utf-8 -*-
#
#     Copyright (c) 2014 Anders Høst
#
# This file is from https://github.com/flababah/cpuid.py commit 09f07f6
#
# It is the concatenation of cpuid.py and example.py, with the name == main
# section removed.
#
# The MIT License (MIT)
#
# Copyright (c) 2014 Anders Høst
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import struct
import platform
import os
import ctypes
from ctypes import c_uint32, c_long, POINTER, CFUNCTYPE

# Posix x86_64:
# Two first call registers : RDI, RSI
# Volatile registers       : RAX, RCX, RDX, RSI, RDI, R8-11

# Windows x86_64:
# Two first call registers : RCX, RDX
# Volatile registers       : RAX, RCX, RDX, R8-11

# cdecl 32 bit:
# Two first call registers : Stack (%esp)
# Volatile registers       : EAX, ECX, EDX

_POSIX_64_OPC = [
        0x53,                    # push   %rbx
        0x48, 0x89, 0xf0,        # mov    %rsi,%rax
        0x0f, 0xa2,              # cpuid
        0x89, 0x07,              # mov    %eax,(%rdi)
        0x89, 0x5f, 0x04,        # mov    %ebx,0x4(%rdi)
        0x89, 0x4f, 0x08,        # mov    %ecx,0x8(%rdi)
        0x89, 0x57, 0x0c,        # mov    %edx,0xc(%rdi)
        0x5b,                    # pop    %rbx
        0xc3                     # retq
]

_WINDOWS_64_OPC = [
        0x53,                    # push   %rbx
        0x48, 0x89, 0xd0,        # mov    %rdx,%rax
        0x49, 0x89, 0xc8,        # mov    %rcx, %r8
        0x0f, 0xa2,              # cpuid
        0x41, 0x89, 0x00,        # mov    %eax,(%r8)
        0x41, 0x89, 0x58, 0x04,  # mov    %ebx,0x4(%r8)
        0x41, 0x89, 0x48, 0x08,  # mov    %ecx,0x8(%r8)
        0x41, 0x89, 0x50, 0x0c,  # mov    %edx,0xc(%r8)
        0x5b,                    # pop    %rbx
        0xc3                     # retq
]

_CDECL_32_OPC = [
        0x53,                    # push   %ebx
        0x57,                    # push   %edi
        0x8b, 0x7c, 0x24, 0x0c,  # mov    0xc(%esp),%edi
        0x8b, 0x44, 0x24, 0x10,  # mov    0x10(%esp),%eax
        0x0f, 0xa2,              # cpuid
        0x89, 0x07,              # mov    %eax,(%edi)
        0x89, 0x5f, 0x04,        # mov    %ebx,0x4(%edi)
        0x89, 0x4f, 0x08,        # mov    %ecx,0x8(%edi)
        0x89, 0x57, 0x0c,        # mov    %edx,0xc(%edi)
        0x5f,                    # pop    %edi
        0x5b,                    # pop    %ebx
        0xc3                     # ret
]

is_windows = os.name == "nt"
is_64bit   = ctypes.sizeof(ctypes.c_voidp) == 8


class DwordRegisters(ctypes.Structure):
    _fields_ = [(r, c_uint32) for r in ("eax", "ebx", "ecx", "edx")]


class RegistersFunction(object):

    def __init__(self):
        if platform.machine() not in ("AMD64", "x86_64", "x86", "i686"):
            raise SystemError("Only available for x86")

        opc = self._get_opcodes()
        code = b"".join((chr(x) for x in opc))
        size = len(code)
        self.r = DwordRegisters()
        self.win = self._get_win()
        self.addr = self._get_addr(self, size)
        assert self.addr
        ctypes.memmove(self.addr, code, size)
        func_type = CFUNCTYPE(None, POINTER(DwordRegisters), c_uint32)
        self.func_ptr = func_type(self.addr)

    def _get_opcodes(self):
        raise NotImplemented

    def _get_win(self):
        if not is_windows:
            return None
        if is_64bit:
            # VirtualAlloc seems to fail under some weird
            # circumstances when ctypes.windll.kernel32 is
            # used under 64 bit Python. CDLL fixes this.
            return ctypes.CDLL("kernel32.dll")
        # Here ctypes.windll.kernel32 is needed to get the
        # right DLL. Otherwise it will fail when running
        # 32 bit Python on 64 bit Windows.
        return ctypes.windll.kernel32

    def _get_addr(self, size):
        if is_windows:
            return self.win.VirtualAlloc(None, size, 0x1000, 0x40)
        addr = ctypes.pythonapi.valloc(size)
        ctypes.pythonapi.mprotect(addr, size, 1 | 2 | 4)
        return addr

    def __call__(self, eax):
        self.func_ptr(self.r, eax)
        return (self.r.eax, self.r.ebx, self.r.ecx, self.r.edx)

    def __del__(self):
        if self.win:  # On Windows
            self.win.VirtualFree(self.addr, 0, 0x8000)
        elif ctypes.pythonapi:
            # Seems to throw exception when the program ends and
            # pythonapi is cleaned up before the object?
            ctypes.pythonapi.free(self.addr)


class CPUID(RegistersFunction):
    def _get_opcodes(self):
        if not is_windows:
            return _POSIX_64_OPC if is_64bit else _CDECL_32_OPC
        return _WINDOWS_64_OPC if is_64bit else _CDECL_32_OPC


class XGETBV(RegistersFunction):
    _WINDOWS_64_OPC = [
        0x53,                    # push   %rbx
        0x48, 0x89, 0xd0,        # mov    %rdx,%rax
        0x49, 0x89, 0xc8,        # mov    %rcx, %r8
        0x0f, 0x01, 0xd0,        # xgetbv
        0x41, 0x89, 0x00,        # mov    %eax,(%r8)
        0x41, 0x89, 0x58, 0x04,  # mov    %ebx,0x4(%r8)
        0x41, 0x89, 0x48, 0x08,  # mov    %ecx,0x8(%r8)
        0x41, 0x89, 0x50, 0x0c,  # mov    %edx,0xc(%r8)
        0x5b,                    # pop    %rbx
        0xc3                     # retq
    ]

    def get_opcodes(self):
        return



def cpu_vendor(cpu):
    _, b, c, d = cpu(0)
    return struct.pack("III", b, d, c)

def cpu_name(cpu):
    return "".join((struct.pack("IIII", *cpu(0x80000000 + i))
            for i in range(2, 5))).strip()

def is_set(cpu, id, reg_idx, bit):
    regs = cpu(id)

    if (1 << bit) & regs[reg_idx]:
        return "Yes"
    else:
        return "--"
