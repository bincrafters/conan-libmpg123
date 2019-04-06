#include <iostream>
#include <mpg123.h>

int main()
{
    const char ** available_decoders = mpg123_decoders();
    const char ** supported_decoders = mpg123_supported_decoders();
    std::cout << "available decoders:" << std::endl;
    for (int i = 0; available_decoders[i] != NULL; ++i)
        std::cout << "\t" << available_decoders[i] << std::endl;
    std::cout << "supported decoders:" << std::endl;
    for (int i = 0; supported_decoders[i] != NULL; ++i)
        std::cout << "\t" << supported_decoders[i] << std::endl;

    return 0;
}
