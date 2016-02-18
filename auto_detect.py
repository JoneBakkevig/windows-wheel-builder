from .cpuid import CPUID, cpu_vendor, cpu_name, is_set


def have_cpuid(cpu):
    return cpu(0)[0] != 0


def get_vendor(cpu):
    vendor = cpu_vendor(cpu)
    if vendor == "GenuineIntel":
        return 'intel'
    if vendor == "AuthenticAMD":
        return 'amd'
    eax, ebx, ecx, edx = cpu(0)
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
    # xgetbv(0, &eax, &edx);
    # if((eax & 6) == 6){
    #  ret=1;  //OS support AVX
    # }
    return True


def bitmask(a, b, c):
    return (a >> b) & c


def cpu_detect(cpu):
    if not have_cpuid():
        return 'reference'
    vendor = get_vendor(cpu)
    eax, ebx, ecx, edx = cpu(1)
    extend_family = bitmask( eax, 20, 0xff )
    extend_model  = bitmask( eax, 16, 0x0f )
    family        = bitmask( eax,  8, 0x0f )
    model         = bitmask( eax,  4, 0x0f )
    return (vendor, extend_family, extend_model, family, model)

"""
  if vendor == 'intel':
    switch (family) {
    case 0x6:
      switch (extend_model) {
      case 1:
        switch (model) {
        case 7:
          //penryn uses dunnington config.
          return CPUNAME_DUNNINGTON;
        case 13:
          return CPUNAME_DUNNINGTON;
        }
        break;
      case 2:
        switch (model) {
        case 10:
        case 13:
          if(support_avx()) {
            return CPUNAME_SANDYBRIDGE;
          }else{
            return CPUNAME_REFERENCE; //OS doesn't support AVX
          }
        }
        break;
      case 3:
        switch (model) {
        case 10:
        case 14:
          //Ivy Bridge
          if(support_avx()) {
            return CPUNAME_SANDYBRIDGE;
          }else{
            return CPUNAME_REFERENCE; //OS doesn't support AVX
          }
        case 12:
        case 15:
          //Haswell
	case 13: //Broadwell
          if(support_avx()) {
            return CPUNAME_HASWELL;
          }else{
            return CPUNAME_REFERENCE; //OS doesn't support AVX
          }

        }
        break;
      case 4:
        switch (model) {
        case 5:
        case 6:
          //Haswell
	case 7:
	case 15:
	  //Broadwell
          if(support_avx()) {
            return CPUNAME_HASWELL;
          }else{
            return CPUNAME_REFERENCE; //OS doesn't support AVX
          }
        }
        break;
      case 5:
	switch (model) {
	case 6:
	  //Broadwell
          if(support_avx()) {
            return CPUNAME_HASWELL;
          }else{
            return CPUNAME_REFERENCE; //OS doesn't support AVX
          }
	}
	break;
      }
      break;
    }
  }else if (vendor == VENDOR_AMD){
    switch (family) {
    case 0xf:
      switch (extend_family) {
      case 6:
        switch (model) {
        case 1:
          if(support_avx())
            return CPUNAME_BULLDOZER;
          else
            return CPUNAME_REFERENCE; //OS don't support AVX.
        case 2:
          if(support_avx())
            return CPUNAME_PILEDRIVER;
          else
            return CPUNAME_REFERENCE; //OS don't support AVX.
        case 0:
          //Steamroller. Temp use Piledriver.
          if(support_avx())
            return CPUNAME_PILEDRIVER;
          else
            return CPUNAME_REFERENCE; //OS don't support AVX.
        }
      }
      break;
    }
  }

  return CPUNAME_REFERENCE;
}
"""

cpu = CPUID()
print(cpu_detect(cpu))
