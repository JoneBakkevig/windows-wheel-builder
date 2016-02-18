import struct

from cpuid import CPUID


def have_cpuid(cpu):
    return cpu(0)[0] != 0


def get_vendor(cpu):
    eax, ebx, ecx, edx = cpu(0)
    vendor = struct.pack("III", ebx, edx, ecx)
    if vendor == "GenuineIntel":
        return 'intel'
    if vendor == "AuthenticAMD":
        return 'amd'
    if eax == 0 or (eax & 0x500) != 0:
        return 'intel'
    return 'unknown'


def all_set(cpu, id, reg_idx, bits):
    regs = cpu(id)
    for bit in bits:
        if not ((1 << bit) & regs[reg_idx]):
            return False
    return True


def support_avx(cpu):
    """ Return True if CPU support AVX

    See:
    * https://en.wikipedia.org/wiki/CPUID
    * https://software.intel.com/en-us/blogs/2011/04/14/is-avx-enabled/
    """
    if not all_set(cpu, 1, 2, [26, 27, 28]):
        return False
    # See: http://www.felixcloutier.com/x86/XGETBV.html
    # xgetbv(0, &eax, &edx);
    # if((eax & 6) == 6){
    #  ret=1;  //OS support AVX
    # }
    return True


def bitmask(a, b, c):
    return (a >> b) & c


CHIP2TEMPLATE = dict(
    ivybridge='haswell',
    broadwell='haswell',
    penryn='dunnington',
    steamroller='piledriver')

NEEDS_AVX = ('sandybridge', 'haswell', 'bulldozer', 'piledriver')

# Intel: family, model, extended model
FAM_MOD_EXTMOD = {
    (6, 7, 1): 'penryn',
    (6, 13, 1): 'dunnington',
    (6, 10, 2): 'sandybridge',
    (6, 13, 2): 'sandybridge',
    (6, 10, 3): 'sandybridge',
    (6, 14, 3): 'sandybridge',
    (6, 12, 3): 'ivybridge',
    (6, 15, 3): 'ivybridge',
    (6, 13, 3): 'broadwell',
    (6, 5, 4): 'haswell',
    (6, 6, 4): 'haswell',
    (6, 7, 4): 'broadwell',
    (6, 15, 4): 'broadwell',
    (6, 6, 5): 'broadwell',
}

# AMD: family, model, extended family
FAM_MOD_EXTFAM = {
    (15, 1, 6): 'bulldozer',
    (15, 2, 6): 'piledriver',
    (15, 0, 6): 'steamroller',
}


def cpu_detect(cpu):
    if not have_cpuid(cpu):
        return 'reference'
    vendor = get_vendor(cpu)
    if vendor not in ('intel', 'amd'):
        return 'reference'
    eax, ebx, ecx, edx = cpu(1)
    extend_family = bitmask(eax, 20, 0xff)
    extend_model  = bitmask(eax, 16, 0x0f)
    processor_type = bitmask(eax, 12, 0x03)
    family = bitmask(eax, 8, 0x0f)
    model = bitmask(eax,  4, 0x0f)
    stepping  = bitmask(eax,  0, 0x0f)
    have_avx = support_avx(cpu)
    if vendor == 'intel':
        chip = FAM_MOD_EXTMOD.get((family, model, extend_model),
                                  'reference')
    else:  # AMD
        chip = FAM_MOD_EXTFAM.get((family, model, extend_family),
                                  'reference')
    template = CHIP2TEMPLATE.get(chip, chip)
    return ('reference' if (template in NEEDS_AVX and not have_avx)
            else template)


cpu = CPUID()
print(cpu_detect(cpu))
