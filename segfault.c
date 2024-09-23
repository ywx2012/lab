void f() {
    int *p = 0;
    *p = 1;
}
void g() { f(); }
void h() { g(); }
int main() { h(); }