using LinearAlgebra

# Keep the residual separate from the solution error.
function relative_residual(A, x, b)
    r = b - A * x
    scale = norm(b)
    return iszero(scale) ? norm(r) : norm(r) / scale
end

A = [4.0 1.0; 2.0 3.0]
b = [1.0, 2.0]
x = A \ b

label = "relative residual"
println(label, ": ", relative_residual(A, x, b))
