package engine

import (
	"math"
	"sync"
)

type object interface {
	GetX() int32
	GetY() int32
	GetWidth() int32
	GetHeight() int32
}

type Vector struct {
	X int32
	Y int32
}

type SpatialHash struct {
	Width    int32
	Height   int32
	CellSize int32
	Objects  map[int32][]object
	sync.RWMutex
}

func (sh *SpatialHash) hashID(v *Vector) int32 {
	return int32(math.Floor(float64(v.X/sh.CellSize))) +
		int32(math.Floor(float64(v.Y/sh.CellSize)))*sh.Width
}

func (sh *SpatialHash) Get(key int32) ([]object, bool) {
	sh.RLock()
	defer sh.RUnlock()

	value, ok := sh.Objects[key]
	return value, ok
}

func (sh *SpatialHash) Set(key int32, value []object) {
	sh.Lock()
	defer sh.Unlock()

	sh.Objects[key] = value
}

func (sh *SpatialHash) HashIds(o object) []int32 {
	ids := []int32{}
	min := &Vector{o.GetX(), o.GetY()}
	max := &Vector{o.GetX() + o.GetWidth(), o.GetY() + o.GetHeight()}

	_append := func(slice []int32, i int32) []int32 {
		for _, other := range slice {
			if other == i {
				return slice
			}
		}

		return append(slice, i)
	}

	add := func(v *Vector) {
		ids = _append(ids, sh.hashID(v))
	}

	for x := min.X; x < max.X+1; x++ {
		for y := min.Y; y < max.Y+1; y++ {
			add(&Vector{x, y})
		}
	}

	return ids
}

func (sh *SpatialHash) Add(o object) {
	ids := sh.HashIds(o)
	for _, id := range ids {
		objects, _ := sh.Get(id)
		sh.Set(id, append(objects, o))
	}
}

func (sh *SpatialHash) Remove(o object) {
	ids := sh.HashIds(o)
	for _, id := range ids {
		objects, _ := sh.Get(id)
		for j, other := range objects {
			if o == other {
				sh.Set(id, append(objects[:j], objects[j+1:]...))
			}
		}
	}
}

func (sh *SpatialHash) Update(o object, f func()) {
	sh.Remove(o)
	{
		f()
	}
	sh.Add(o)
}

func (sh *SpatialHash) Nearby(o object) []object {
	newObjs := []object{}
	ids := sh.HashIds(o)

	_append := func(slice []object, o object) []object {
		for _, other := range slice {
			if other == o {
				return slice
			}
		}

		return append(slice, o)
	}

	for _, id := range ids {
		objects, _ := sh.Get(id)
		for _, object := range objects {
			if object != o {
				newObjs = _append(newObjs, object)
			}
		}
	}

	return newObjs
}

func NewSpatialHash(width int32, height int32, cellSize int32) *SpatialHash {
	return &SpatialHash{
		Width:    width,
		Height:   height,
		CellSize: cellSize,
		Objects:  make(map[int32][]object),
	}
}
