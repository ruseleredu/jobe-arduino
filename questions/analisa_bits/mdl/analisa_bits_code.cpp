#include <stdio.h>
#include <stdint.h>

int main(void) {
    uint8_t reg  = 0b10110010;
    uint8_t mask = 0b00001111;   // isola os 4 bits baixos
    printf("%d\n", reg & mask);
    return 0;
}
