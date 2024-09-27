const std = @import("std");
const S = struct { a: usize, b: usize, c: usize, };
pub fn main() !void {
    const stdout = std.io.getStdOut().writer();
    const s: S = .{ .a = 1, .b = 2, .c = 3,};
    try stdout.print("{}\n", .{s});
}