const c = @cImport({
    @cInclude("segfault.h");
});

pub fn main() !void {
    c.h();
}
